"""
task_orchestrator.py
====================
Handles multi-step tasks that require chaining multiple tools together.
For example: "open whatsapp and send hi to John"
"""

import asyncio
import json
import os
from typing import List, Dict, Any
from groq import Groq
from tools.registry import registry
from tools.generator import generator

class TaskOrchestrator:
    """
    Breaks complex multi-step queries into sequential tool executions.
    Auto-generates new tools when needed.
    """

    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    async def execute_multi_step(self, user_query: str) -> Dict[str, Any]:
        """
        Main entry point for complex tasks.
        
        Example queries:
        - "open whatsapp and send hi to John"
        - "open chrome, go to youtube, and search for music"
        - "find report.xlsx, open it, and color the headers red"
        """
        print(f"\n[Orchestrator] Multi-step task: '{user_query}'")

        # Step 1: Ask LLM to break down the task into steps
        steps = await self._decompose_task(user_query)
        
        if not steps:
            return {
                "success": False,
                "error": "Could not decompose task into steps"
            }

        print(f"[Orchestrator] Decomposed into {len(steps)} steps:")
        for i, step in enumerate(steps, 1):
            print(f"  {i}. {step.get('description', 'Unknown step')}")

        # Step 2: Execute steps sequentially
        results = []
        for i, step in enumerate(steps, 1):
            print(f"\n[Orchestrator] Executing step {i}/{len(steps)}: {step.get('description', '')}")
            
            result = await self._execute_single_step(step)
            results.append(result)
            
            # If step failed, stop execution
            if not result.get("success", False):
                print(f"[Orchestrator] ❌ Step {i} failed: {result.get('error')}")
                break
            
            print(f"[Orchestrator] ✅ Step {i} completed")
            
            # Small delay between steps for UI to update
            if i < len(steps):
                await asyncio.sleep(1.5)

        # Step 3: Return combined results
        success = all(r.get("success", False) for r in results)
        return {
            "success": success,
            "steps": len(steps),
            "results": results,
            "summary": self._generate_summary(user_query, results)
        }

    async def _decompose_task(self, user_query: str) -> List[Dict]:
        """
        Uses LLM to break a complex query into sequential steps.
        Returns list of step objects with tool names and parameters.
        """
        # Get available tools for context
        tools = registry.get_definitions()
        tool_names = [t["name"] for t in tools]

        prompt = f"""You are a task decomposition AI.

User query: "{user_query}"

Available tools: {', '.join(tool_names)}

Break this query into sequential steps. Each step should use ONE tool.
If a tool doesn't exist yet (like send_whatsapp_message), specify it anyway — we'll generate it.

Return ONLY a JSON array of steps:
[
  {{
    "step": 1,
    "description": "Open WhatsApp application",
    "tool": "open_app",
    "params": {{"target": "whatsapp"}}
  }},
  {{
    "step": 2,
    "description": "Send message to contact",
    "tool": "send_whatsapp_message",
    "params": {{"contact": "Little girl akka", "message": "hi"}}
  }}
]

Return ONLY the JSON array, no explanation."""

        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_completion_tokens=800
            )

            content = response.choices[0].message.content.strip()
            # Clean markdown
            content = content.replace("```json", "").replace("```", "").strip()
            
            steps = json.loads(content)
            return steps if isinstance(steps, list) else []

        except Exception as e:
            print(f"[Orchestrator] Decomposition error: {e}")
            return []

    async def _execute_single_step(self, step: Dict) -> Dict[str, Any]:
        """Execute a single step — generate tool if needed."""
        tool_name = step.get("tool")
        params    = step.get("params", {})

        if not tool_name:
             return {"success": False, "error": "No tool specified in step"}

        # Check if tool exists
        if not registry.has_tool(tool_name):
            print(f"[Orchestrator] Tool '{tool_name}' not found — generating...")
            
            # Generate new tool
            description = step.get("description", f"Implement {tool_name}")
            tool_def = await generator.generate_tool(description)
            
            if not tool_def:
                return {
                    "success": False,
                    "error": f"Failed to generate tool '{tool_name}'"
                }
            
            print(f"[Orchestrator] ✅ Generated tool: {tool_def['name']}")
            tool_name = tool_def["name"]  # use actual generated name

        # Execute tool
        try:
            # Check if executor is loaded
            if tool_name not in registry.executors:
                registry._load_executor(tool_name)
                
            result = await registry.execute(tool_name, params)
            return {
                "success": True,
                "tool": tool_name,
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "tool": tool_name,
                "error": str(e)
            }

    def _generate_summary(self, query: str, results: List[Dict]) -> str:
        """Generate human-readable summary of execution."""
        success_count = sum(1 for r in results if r.get("success"))
        total         = len(results)

        if success_count == total:
            return f"✅ Completed all {total} steps for: '{query}'"
        elif success_count == 0:
            return f"❌ Failed to execute: '{query}'"
        else:
            return f"⚠️ Completed {success_count}/{total} steps for: '{query}'"


# Global instance
orchestrator = TaskOrchestrator()
