"""
src/core/execution/multistep_executor.py
=========================================
Executes a MultiStepPlan step by step, passing results between steps.

Features:
  - Runs each step through the existing handle_action() dispatcher
  - Stores step outputs in a shared context dict
  - Injects previous step results into next steps (e.g. stock price → excel value)
  - Emits real-time events to frontend for each step
  - Continues on soft failures, stops on critical ones
  - Returns structured step list matching agent.py's intermediate_steps format
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional

from src.core.execution.multistep_planner import MultiStepPlan, PlanStep


# ─────────────────────────────────────────────────────────────────────────────
# EXECUTOR
# ─────────────────────────────────────────────────────────────────────────────

async def execute_multistep_plan(
    plan:     MultiStepPlan,
    task_id:  str,
    emit_event  # the emit_event function from events.py
) -> List[Dict[str, Any]]:
    """
    Execute a MultiStepPlan sequentially.

    Args:
        plan:       The decomposed plan from multistep_planner.plan_multistep()
        task_id:    Task ID for event emission
        emit_event: Async function to push events to frontend

    Returns:
        List of step dicts in agent.py's intermediate_steps format:
        [{"type": "Action", "content": "...", "timestamp": "...", "attachment": ...}]
    """
    from src.core.execution.handlers import handle_action

    steps_output:  List[Dict[str, Any]] = []
    step_context:  Dict[str, Any]       = {}   # Shared data passed between steps
    total                               = len(plan.steps)

    await emit_event(task_id, "MultiStepStart", {
        "intent":      plan.intent,
        "total_steps": total,
        "query":       plan.original_query,
    })

    for i, step in enumerate(plan.steps, start=1):
        await emit_event(task_id, "StepStarted", {
            "step":        i,
            "total":       total,
            "action":      step.action,
            "description": step.description,
        })

        # ── Inject data from a previous step if requested ─────────────────────
        target, context = _inject_context(step, step_context)

        # ── Execute via handle_action ─────────────────────────────────────────
        try:
            handler_result = await handle_action(
                action     = step.action,
                target     = target,
                context    = context,
                user_input = plan.original_query,
                task_id    = task_id,
            )

            result_text = handler_result.get("result", "")
            attachment  = handler_result.get("attachment")
            tool_used   = handler_result.get("tool_used", step.action)
            success     = "❌" not in result_text

            # ── Store output for next steps ───────────────────────────────────
            if step.output_key:
                step_context[step.output_key] = result_text
            # Always store by action name as fallback
            step_context[f"step_{i}_result"] = result_text

        except Exception as e:
            result_text = f"❌ Step {i} error: {e}"
            attachment  = None
            tool_used   = step.action
            success     = False

        # ── Emit result event ─────────────────────────────────────────────────
        await emit_event(task_id, "StepResult", {
            "step":        i,
            "total":       total,
            "action":      step.action,
            "description": step.description,
            "result":      result_text,
            "success":     success,
        })

        # ── Build step record for agent.py's intermediate_steps ───────────────
        steps_output.append({
            "type":        "Action",
            "content":     f"**Step {i}/{total} — {step.description}**\n{result_text}",
            "timestamp":   datetime.now().strftime("%I:%M:%S %p"),
            "attachment":  attachment,
            "tool":        tool_used,
            "step_number": i,
            "success":     success,
        })

        # ── Small delay between steps so UI updates are visible ───────────────
        await asyncio.sleep(0.5)

    # ── Final summary event ───────────────────────────────────────────────────
    succeeded = sum(1 for s in steps_output if s.get("success"))
    await emit_event(task_id, "MultiStepComplete", {
        "intent":    plan.intent,
        "succeeded": succeeded,
        "total":     total,
        "summary":   f"Completed {succeeded}/{total} steps for: {plan.original_query}",
    })

    return steps_output


# ─────────────────────────────────────────────────────────────────────────────
# CONTEXT INJECTION
# ─────────────────────────────────────────────────────────────────────────────

def _inject_context(
    step:         PlanStep,
    step_context: Dict[str, Any]
) -> tuple[str, Optional[str]]:
    """
    Resolve target/context by injecting results from previous steps.
    
    Example:
      step.depends_on = "excel_path"   → replaces target with stored excel path
      step.target = "{step_1_result}"  → injects step 1's output into target
    """
    target  = step.target  or ""
    context = step.context

    # Inject from depends_on key
    if step.depends_on and step.depends_on in step_context:
        injected = str(step_context[step.depends_on])
        # Replace placeholder in target/context or prepend
        if "{depends}" in target:
            target = target.replace("{depends}", injected)
        elif "{depends}" in (context or ""):
            context = context.replace("{depends}", injected)
        else:
            # Default: prepend to context
            context = f"{injected},{context}" if context else injected

    # Resolve {step_N_result} placeholders in target/context
    import re
    for key, value in step_context.items():
        placeholder = "{" + key + "}"
        if placeholder in target:
            target  = target.replace(placeholder, str(value))
        if context and placeholder in context:
            context = context.replace(placeholder, str(value))

    return target, context
