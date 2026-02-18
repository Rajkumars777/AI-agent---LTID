"""
Agentic Orchestrator
====================
Master controller that plans and executes complex multi-step web automation tasks.
Uses LLM reasoning for dynamic planning, state management, and error recovery.
"""

import asyncio
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from llm.agent_llm import (
    plan_task, TaskPlan, AgentStep, 
    verify_action, error_recovery_planner
)
from execution.task_memory import TaskMemory, get_task_memory


@dataclass
class StepResult:
    """Result of executing a single step"""
    step_number: int
    action: str
    success: bool
    result: str
    extracted_data: Dict[str, Any]
    error: Optional[str] = None
    retry_count: int = 0


@dataclass
class TaskResult:
    """Final result of task execution"""
    success: bool
    summary: str
    extracted: Dict[str, Any]
    logs: List[str]
    attachment: Optional[Dict] = None
    error: Optional[str] = None


class AgenticOrchestrator:
    """
    Orchestrates complex multi-step browser automation tasks with:
    - Dynamic planning using LLM
    - State management across steps
    - Conditional execution
    - Error recovery and retries
    """
    
    def __init__(self, browser_agent=None):
        self.browser_agent = browser_agent
        self.max_retries = 3
        self.max_replans = 2
        
    async def execute_task(self, goal: str, starting_url: Optional[str] = None, 
                          task_id: str = "default") -> TaskResult:
        """
        Main entry point: Plan and execute a complete task.
        
        Args:
            goal: Natural language description of the task
            starting_url: Optional starting URL
            task_id: Unique task identifier
        
        Returns:
            TaskResult with success status, extracted data, and logs
        """
        memory = get_task_memory(task_id, create=True)
        memory.update_state(goal=goal, status="planning")
        logs = []
        
        try:
            # 1. PLAN the task
            logs.append(f"🎯 Goal: {goal}")
            current_context = self._build_context(memory, starting_url)
            plan = plan_task(goal, current_context)
            
            logs.append(f"📋 Planned {len(plan.steps)} steps (Type: {plan.task_type})")
            memory.update_state(total_steps=len(plan.steps), status="executing")
            
            # 2. EXECUTE the plan
            step_results: List[StepResult] = []
            for i, step in enumerate(plan.steps):
                memory.update_state(current_step=i + 1)
                logs.append(f"\n--- Step {step.step_number}: {step.action} ---")
                
                # Execute step with retries
                result = await self._execute_step_with_retries(
                    step, memory, plan, logs
                )
                step_results.append(result)
                
                # Check if step failed critically
                if not result.success and result.retry_count >= self.max_retries:
                    logs.append(f"❌ Step {step.step_number} failed after {result.retry_count} retries")
                    
                    # Try to replan if we haven't exceeded max replans
                    if len([r for r in step_results if not r.success]) <= self.max_replans:
                        logs.append("🔄 Attempting to replan remaining steps...")
                        new_plan = await self._replan_task(
                            original_plan=plan,
                            failed_step=step,
                            error=result.error or "Unknown error",
                            memory=memory
                        )
                        if new_plan and new_plan.steps:
                            logs.append(f"📋 New plan: {len(new_plan.steps)} steps")
                            plan.steps = plan.steps[:i+1] + new_plan.steps  # Replace remaining steps
                            continue
                    
                    # Can't recover, partial success
                    logs.append("⚠️ Proceeding with partial results")
                
                # Store extracted data
                for key, value in result.extracted_data.items():
                    memory.store_extracted_data(
                        key, value, 
                        memory.current_url or starting_url or "unknown",
                        data_type="auto"
                    )
            
            # 3. FINALIZE and return results
            extracted_all = memory.get_all_extracted_data()
            successful_steps = [r for r in step_results if r.success]
            
            success = len(successful_steps) >= len(plan.steps) * 0.7  # 70% success threshold
            
            summary = self._build_summary(goal, plan, step_results, extracted_all)
            logs.append(f"\n✅ Task completed: {len(successful_steps)}/{len(plan.steps)} steps successful")
            
            memory.update_state(status="completed" if success else "partial")
            
            return TaskResult(
                success=success,
                summary=summary,
                extracted=extracted_all,
                logs=logs,
                attachment=self._create_attachment(extracted_all)
            )
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            logs.append(f"💥 Critical error: {e}")
            logs.append(error_trace)
            
            memory.update_state(status="failed", error=str(e))
            
            return TaskResult(
                success=False,
                summary=f"Task failed: {e}",
                extracted=memory.get_all_extracted_data(),
                logs=logs,
                error=error_trace
            )
    
    async def _execute_step_with_retries(self, step: AgentStep, memory: TaskMemory,
                                        plan: TaskPlan, logs: List[str]) -> StepResult:
        """Execute a single step with automatic retries on failure"""
        
        for retry in range(self.max_retries):
            try:
                # Check if we need data from previous steps
                if step.required_data:
                    missing = [d for d in step.required_data if not memory.get_extracted_data(d)]
                    if missing:
                        logs.append(f"⚠️ Missing required data: {missing}")
                        return StepResult(
                            step_number=step.step_number,
                            action=step.action,
                            success=False,
                            result="Missing required data",
                            extracted_data={},
                            error=f"Missing: {missing}",
                            retry_count=retry
                        )
                
                # Execute the step
                logs.append(f"🚀 Executing: {step.action} on {step.target}")
                result_text, extracted = await self._execute_single_step(
                    step, memory, logs
                )
                
                # Verify success
                page_state = f"URL: {memory.current_url}, Title: {result_text[:100]}"
                success = verify_action(
                    action=f"{step.action} {step.target}",
                    page_state=page_state,
                    expected=step.expected_outcome
                )
                
                if success or retry == self.max_retries - 1:
                    logs.append(f"{'✅' if success else '⚠️'} Result: {result_text[:200]}")
                    memory.log_action(
                        action=f"{step.action} {step.target}",
                        result=result_text,
                        metadata={"step": step.step_number, "retry": retry}
                    )
                    
                    return StepResult(
                        step_number=step.step_number,
                        action=step.action,
                        success=success,
                        result=result_text,
                        extracted_data=extracted,
                        retry_count=retry
                    )
                else:
                    logs.append(f"🔄 Retry {retry + 1}/{self.max_retries}")
                    await asyncio.sleep(1)  # Brief pause before retry
                    
            except Exception as e:
                logs.append(f"❌ Step error (attempt {retry + 1}): {e}")
                if retry == self.max_retries - 1:
                    return StepResult(
                        step_number=step.step_number,
                        action=step.action,
                        success=False,
                        result=str(e),
                        extracted_data={},
                        error=str(e),
                        retry_count=retry
                    )
        
        # Should not reach here
        return StepResult(
            step_number=step.step_number,
            action=step.action,
            success=False,
            result="Max retries exceeded",
            extracted_data={},
            retry_count=self.max_retries
        )
    
    async def _execute_single_step(self, step: AgentStep, memory: TaskMemory,
                                   logs: List[str]) -> tuple[str, Dict]:
        """Execute a single step action"""
        from capabilities.browser_agent import browser_agent
        
        action = step.action.lower()
        target = step.target
        params = step.parameters
        extracted = {}
        
        # Map action to browser agent method
        # Map action to browser agent method
        if action in ["navigate", "go", "visit", "open"]:
            # Navigation action
            result = await asyncio.to_thread(
                browser_agent.navigate, target
            )
            memory.add_visited_url(target)
            
        elif action in ["search", "find", "query"]:
            # Search action
            site = browser_agent._identify_site(memory.current_url or "")
            query = params.get("query", target)
            result = await asyncio.to_thread(
                browser_agent._do_search, site, query
            )
            
        elif action in ["click", "select", "click_first"]:
            # Click action - Try Browser first, then fallback to Desktop/Visual if requested or failed
            # For now, we assume if the action specifically says "click_text" or "click_icon", it's desktop
            # But standard "click" goes to browser
            site = browser_agent._identify_site(memory.current_url or "")
            result = await asyncio.to_thread(
                browser_agent._do_click_first, site
            )

        # --- Visual / Desktop Capabilities ---
        elif action in ["click_text", "desktop_click"]:
            from capabilities.desktop_automation import desktop_agent
            result = await asyncio.to_thread(
                desktop_agent.click_text, target
            )

        elif action in ["type_desktop", "desktop_type"]:
            from capabilities.desktop_automation import desktop_agent
            result = await asyncio.to_thread(
                desktop_agent.type_text, target
            )

        elif action in ["press_key", "send_key"]:
            from capabilities.desktop_automation import desktop_agent
            result = await asyncio.to_thread(
                desktop_agent.press_key, target
            )

        elif action in ["read_screen", "ocr_screen"]:
            from capabilities.vision_engine import vision_engine
            result = await asyncio.to_thread(
                vision_engine.read_screen_text
            )
            extracted["screen_text"] = result
        # -------------------------------------
            
        elif action in ["extract", "get_data", "scrape"]:
            # Extract action
            site = browser_agent._identify_site(memory.current_url or "")
            data_type = params.get("data_type", target)
            value = await asyncio.to_thread(
                browser_agent._do_extract, site, data_type
            )
            extracted[f"{site}_{data_type}"] = value
            result = f"Extracted {data_type}: {value}"
            
        elif action in ["filter", "apply_filter"]:
            # Filter action
            site = browser_agent._identify_site(memory.current_url or "")
            filter_type = params.get("type", "price_under")
            filter_value = params.get("value", target)
            result = await asyncio.to_thread(
                browser_agent._do_filter, site, filter_type, filter_value
            )
            
        elif action in ["compare", "comparison"]:
            # Special handling for comparisons
            comparison_data = memory.compare_data(target)
            result = json.dumps(comparison_data, indent=2)
            extracted["comparison"] = comparison_data
            
        elif action in ["execute", "run", "do"]:
            # Generic execution - parse the target to determine what to do
            # This is the fallback for when LLM creates generic steps
            
            # Check if target contains a URL
            import re
            url_match = re.search(r'(https?://[^\s]+|amazon\.in|flipkart\.com|google\.com|wikipedia\.org)', target, re.IGNORECASE)
            
            if url_match:
                # Has a URL - navigate first if we're not there
                url_part = url_match.group(1)
                if not url_part.startswith('http'):
                    # Site name like "amazon.in"
                    site_map = {
                        "amazon.in": "https://www.amazon.in",
                        "amazon": "https://www.amazon.in",
                        "flipkart.com": "https://www.flipkart.com",
                        "flipkart": "https://www.flipkart.com",
                        "google.com": "https://www.google.com",
                        "google": "https://www.google.com",
                        "wikipedia.org": "https://www.wikipedia.org",
                        "wikipedia": "https://www.wikipedia.org",
                    }
                    for site_name, site_url in site_map.items():
                        if site_name in url_part.lower():
                            url_part = site_url
                            break
                    if not url_part.startswith('http'):
                        url_part = f"https://www.{url_part}"
                
                # Navigate if not already on this site
                current = memory.current_url or ""
                if url_part not in current:
                    logs.append(f"  📍 Navigating to {url_part}")
                    nav_result = await asyncio.to_thread(
                        browser_agent.navigate, url_part
                    )
                    memory.add_visited_url(url_part)
                    logs.append(f"  {nav_result}")
            
            # Check if target contains "search" keyword
            search_match = re.search(r'search\s+(?:for\s+)?["\']?([^"\']+)["\']?', target, re.IGNORECASE)
            if search_match:
                query = search_match.group(1).strip()
                logs.append(f"  🔍 Searching for: {query}")
                site = browser_agent._identify_site(memory.current_url or "")
                result = await asyncio.to_thread(
                    browser_agent._do_search, site, query
                )
            else:
                # Fallback: log error instead of using legacy run_task
                logs.append(f"  ⚠️ Could not determine specific action for: {target}")
                result = f"Action execution failed: Could not determine how to execute '{target}'"
        
        else:
            # Unknown action
            logs.append(f"  ⚠️ Unknown action '{action}'")
            result = f"Action '{action}' is not supported."
        
        return result, extracted
    
    async def _replan_task(self, original_plan: TaskPlan, failed_step: AgentStep,
                          error: str, memory: TaskMemory) -> Optional[TaskPlan]:
        """Replan remaining steps after a failure"""
        try:
            # Use LLM to suggest recovery
            page_state = f"Current URL: {memory.current_url}, Extracted: {memory.get_all_extracted_data()}"
            
            prediction = error_recovery_planner(
                original_action=f"{failed_step.action} {failed_step.target}",
                error=error,
                page_state=page_state
            )
            
            should_retry = prediction.should_retry.lower() in ["yes", "true"]
            
            if should_retry:
                # Create new plan with recovery strategy
                new_context = f"Previous approach failed: {error}. Recovery: {prediction.recovery_strategy}"
                new_plan = plan_task(original_plan.goal, new_context)
                return new_plan
            else:
                return None
                
        except Exception as e:
            print(f"[Orchestrator] Replan failed: {e}")
            return None
    
    def _build_context(self, memory: TaskMemory, starting_url: Optional[str]) -> str:
        """Build context string for planning"""
        context_parts = []
        
        if starting_url:
            context_parts.append(f"Starting URL: {starting_url}")
        
        if memory.current_url:
            context_parts.append(f"Current URL: {memory.current_url}")
        
        extracted = memory.get_all_extracted_data()
        if extracted:
            context_parts.append(f"Extracted data: {json.dumps(extracted, indent=2)}")
        
        return "\n".join(context_parts) if context_parts else "Starting fresh"
    
    def _build_summary(self, goal: str, plan: TaskPlan, results: List[StepResult],
                      extracted: Dict) -> str:
        """Build human-readable summary of execution"""
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        
        summary_parts = [
            f"**Goal**: {goal}",
            f"**Steps Completed**: {len(successful)}/{len(results)}",
        ]
        
        if extracted:
            summary_parts.append(f"**Extracted Data**:")
            for key, value in extracted.items():
                summary_parts.append(f"  - {key}: {value}")
        
        if failed:
            summary_parts.append(f"**Failed Steps**: {len(failed)}")
            for r in failed:
                summary_parts.append(f"  - Step {r.step_number}: {r.error or 'Unknown error'}")
        
        return "\n".join(summary_parts)
    
    def _create_attachment(self, extracted: Dict) -> Optional[Dict]:
        """Create attachment for frontend display"""
        if not extracted:
            return None
        
        return {
            "type": "data_card",
            "title": "Extracted Data",
            "content": json.dumps(extracted, indent=2)
        }


# Global orchestrator instance
orchestrator = AgenticOrchestrator()
