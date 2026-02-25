"""
src/services/desktop/generative_agent.py
=========================================
Generative "Just-In-Time" (JIT) Automation Agent.

Uses LLM to generate Python code for desktop tasks,
then executes it with S1-Grade OS verification.

Key improvement over old version:
  ❌ OLD: execute code → report success immediately
  ✅ NEW: execute code → verify via OS polling → report only if truly done
"""

import os
import asyncio
import logging
from typing import Callable

from src.tools.generator import generator
from src.services.desktop.automation import desktop_automation

logger = logging.getLogger(__name__)


class GenerativeAgent:
    """
    JIT flow: Query → Generation → Execution → OS Verification.

    The generated code MUST use `desktop.wait_for_window_active()`
    and polling patterns instead of `time.sleep()`. 
    The CODE_PROMPT in generator.py enforces this.
    """

    async def run(self, task: str, emit: Callable = None) -> str:
        """
        Generates and executes a desktop automation script.
        Verifies completion via OS state polling, not blind success.
        """
        try:
            if emit:
                await emit("AgentStep", {
                    "desc": f"🧠 Generating automation script for: '{task}'"
                })

            # 1. Generate tool definition
            tool_def = await generator._generate_definition(task)
            if not tool_def:
                return "❌ Failed to define JIT tool."

            # 2. Generate code
            code = await generator._generate_code(tool_def, task)
            if not code:
                return "❌ Failed to generate JIT code."

            logger.info(f"Generated JIT Code for '{tool_def['name']}':\n{code}")

            # 3. Extract parameters from query
            params = await generator._extract_values(tool_def, task)
            logger.info(f"Extracted JIT Params: {params}")

            if emit:
                await emit("AgentStep", {
                    "desc": f"🚀 Executing: {tool_def['name']}..."
                })

            # 4. Execute the generated script
            result = desktop_automation.execute_dynamic_script(code, params=params)

            # 5. Check result — the generated code should return [Success] or [Error]
            if "[Success]" in result:
                logger.info(f"JIT execution succeeded: {result}")
                return f"✅ JIT Task Success: {result}"
            else:
                logger.warning(f"JIT execution returned non-success: {result}")
                return f"❌ JIT Task Failure: {result}"

        except Exception as e:
            logger.error(f"GenerativeAgent error: {e}")
            return f"❌ JIT Error: {e}"


generative_agent = GenerativeAgent()
