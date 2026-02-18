"""
generator.py
============
Auto-generates new Python tools for unknown tasks using LLM.
Includes: safety validation, syntax checking, retry logic, dry-run support.
"""

import os
import ast
import json
import re
import asyncio
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────

GENERATED_TOOLS_DIR = os.path.join(os.path.dirname(__file__), "generated")

# Patterns that are dangerous in auto-generated code
DANGEROUS_PATTERNS = [
    r"rm\s+-rf",                  # unix force delete
    r"del\s+/f",                  # windows force delete
    r"format\s+",                 # disk format
    r"shutil\.rmtree\(",          # recursive folder delete
    r"subprocess\.run\(.*rm",     # shell rm via subprocess
    r"eval\(",                    # dynamic code eval
    r"exec\(",                    # dynamic code exec
    r"os\.remove\(",              # file deletion
    r"os\.rmdir\(",               # folder deletion
    r"os\.system\(",              # raw shell command
    r"__import__\(",              # dynamic imports
    r"open\(.*['\"]w['\"]",       # file overwrite
    r"requests\.delete\(",        # HTTP delete calls
    r"urllib.*delete",            # urllib delete calls
]

# ─────────────────────────────────────────────────────
# PROMPTS
# ─────────────────────────────────────────────────────

DEFINITION_PROMPT = """
You are a tool schema designer for a desktop AI agent.

User wants to: "{query}"

Generate a reusable tool definition JSON for this task.
The tool should work for similar tasks in the future too.

Return ONLY valid JSON in this exact format, nothing else:
{{
  "name": "snake_case_tool_name",
  "description": "What it does. Use when user says: keyword1, keyword2, keyword3",
  "input_schema": {{
    "type": "object",
    "properties": {{
      "param1": {{"type": "string", "description": "what this param is"}},
      "param2": {{"type": "string", "description": "what this param is"}}
    }},
    "required": ["param1"]
  }}
}}

Rules:
- name must be snake_case and clearly describe the action
- description must include "Use when user says:" with 4-6 relevant trigger keywords
- Only include parameters that are actually needed
- Return ONLY the JSON object, no explanation, no markdown
"""

CODE_PROMPT = """
You are a Python code generator for a desktop AI agent on Windows.

Write a complete Python executor for this tool:

Tool name: {name}
Description: {description}
Parameters: {params}
Example task: "{query}"

Requirements:
1. Write a single function called `execute(params: dict) -> str`
2. Use ONLY Python standard library modules (os, shutil, subprocess, glob, pathlib, winreg, ctypes)
3. Access parameters like: params.get("param_name", "default")
4. Return a string starting with [Success] on success
5. Return a string starting with [Error] on failure
6. Wrap everything in try/except
7. No external pip packages
8. No dangerous operations (no file deletion, no format, no eval)

Return ONLY the Python code. No explanation. No markdown. No ```python blocks.
Start directly with imports then the execute function.

Example format:
import os
import shutil

def execute(params: dict) -> str:
    try:
        source = params.get("source", "")
        dest   = params.get("destination", "")
        # ... implementation
        return "[Success] Task completed"
    except Exception as e:
        return f"[Error] {{str(e)}}"
"""


# ─────────────────────────────────────────────────────
# TOOL GENERATOR
# ─────────────────────────────────────────────────────

class ToolGenerator:
    """
    Generates new Python tools for unknown tasks.
    Uses LLM to create both the schema and executor code.
    """

    def __init__(self, registry=None):
        # Injected from outside to avoid circular imports
        self.registry = registry
        self.client   = Groq(api_key=os.getenv("GROQ_API_KEY"))
        os.makedirs(GENERATED_TOOLS_DIR, exist_ok=True)

    # ─────────────────────────────────────────────────
    # PUBLIC: Main entry point
    # ─────────────────────────────────────────────────

    async def generate_tool(self, user_query: str) -> dict | None:
        """
        Full pipeline: query → schema → code → validate → save → register
        Returns tool definition dict on success, None on failure.
        """
        print(f"\n[Generator] Starting evolution for: '{user_query}'")

        # Step 1: Generate tool schema/definition
        tool_def = await self._generate_definition(user_query)
        if not tool_def:
            print("[Generator] ❌ Failed at definition stage")
            return None
        print(f"[Generator] ✅ Schema created: {tool_def['name']}")

        # Step 2: Generate executor code
        code = await self._generate_code(tool_def, user_query)
        if not code:
            print("[Generator] ❌ Failed at code generation stage")
            return None
        print(f"[Generator] ✅ Code generated ({len(code)} chars)")

        # Step 3: Safety check
        safe, blocked = self.is_safe_code(code)
        if not safe:
            print(f"[Generator] ❌ Safety check failed — blocked: {blocked}")
            return None
        print("[Generator] ✅ Safety check passed")

        # Step 4: Syntax validation
        if not self._is_valid_python(code):
            print("[Generator] ❌ Syntax validation failed")
            return None
        print("[Generator] ✅ Syntax valid")

        # Step 5: Check execute() function exists
        if not self._has_execute_function(code):
            print("[Generator] ❌ No execute() function found")
            return None
        print("[Generator] ✅ execute() function found")

        # Step 6: Dry run test
        dry_run_result = self._dry_run(code, tool_def)
        if not dry_run_result["passed"]:
            print(f"[Generator] ❌ Dry run failed: {dry_run_result['error']}")
            return None
        print("[Generator] ✅ Dry run passed")

        # Step 7: Save to disk
        saved = self._save_tool(tool_def["name"], code)
        if not saved:
            print("[Generator] ❌ Failed to save tool file")
            return None
        print(f"[Generator] ✅ Saved to {tool_def['name']}.py")

        # Step 8: Register in registry
        if self.registry:
            self.registry.register(tool_def)
            print(f"[Generator] ✅ Registered: {tool_def['name']}")

        print(f"[Generator] 🎉 Evolution complete: '{tool_def['name']}'")
        return tool_def

    # ─────────────────────────────────────────────────
    # VALIDATION METHODS
    # ─────────────────────────────────────────────────

    def is_safe_code(self, code: str) -> tuple[bool, str | None]:
        """
        Checks for dangerous patterns in generated code.
        Returns (is_safe, blocked_pattern)
        """
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, code, re.IGNORECASE):
                return False, pattern
        return True, None

    def _is_valid_python(self, code: str) -> bool:
        """Checks Python syntax without executing the code."""
        try:
            ast.parse(code)
            return True
        except SyntaxError as e:
            print(f"[Generator] Syntax error at line {e.lineno}: {e.msg}")
            return False

    def _has_execute_function(self, code: str) -> bool:
        """Verifies the generated code contains an execute() function."""
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == "execute":
                    return True
        except Exception:
            pass
        return False

    def _dry_run(self, code: str, tool_def: dict) -> dict:
        """
        Safely test-loads the code in an isolated namespace.
        Does NOT execute execute() — only checks it loads without import errors.
        """
        try:
            namespace = {}
            exec(compile(ast.parse(code), "<generated>", "exec"), namespace)

            # Check execute is callable
            if "execute" not in namespace or not callable(namespace["execute"]):
                return {"passed": False, "error": "execute is not callable"}

            return {"passed": True, "error": None}

        except Exception as e:
            return {"passed": False, "error": str(e)}

    # ─────────────────────────────────────────────────
    # LLM CALLS
    # ─────────────────────────────────────────────────

    async def _generate_definition(self, query: str) -> dict | None:
        """Ask LLM to generate tool schema/definition JSON."""
        prompt = DEFINITION_PROMPT.format(query=query)

        response = await self._call_llm_with_retry(
            prompt          = prompt,
            reasoning_effort = "low",    # schema is simple — low is enough
            temperature     = 0.2,       # deterministic JSON output
        )

        if not response:
            return None

        try:
            cleaned = self._clean_llm_output(response)
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            print(f"[Generator] JSON parse error: {e}")
            print(f"[Generator] Raw output: {response[:200]}")
            return None

    async def _generate_code(self, tool_def: dict, query: str) -> str | None:
        """Ask LLM to generate the Python executor code."""
        prompt = CODE_PROMPT.format(
            name        = tool_def["name"],
            description = tool_def["description"],
            params      = json.dumps(
                tool_def.get("input_schema", {}).get("properties", {}),
                indent=2
            ),
            query       = query
        )

        response = await self._call_llm_with_retry(
            prompt          = prompt,
            reasoning_effort = "medium",  # code needs more reasoning
            temperature     = 0.2,        # deterministic code output
        )

        if not response:
            return None

        return self._clean_llm_output(response)

    async def _call_llm_with_retry(
        self,
        prompt: str,
        reasoning_effort: str = "low",
        temperature: float    = 0.2,
        retries: int          = 3,
        delay: float          = 1.5
    ) -> str | None:
        """
        Calls Groq API with automatic retry on failure.
        Handles rate limits and transient errors.
        """
        for attempt in range(1, retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model            = "llama-3.3-70b-versatile",
                    messages         = [{"role": "user", "content": prompt}],
                    temperature      = temperature,
                    max_completion_tokens = 1024,
                )
                return response.choices[0].message.content

            except Exception as e:
                print(f"[Generator] LLM attempt {attempt}/{retries} failed: {e}")
                if attempt < retries:
                    await asyncio.sleep(delay * attempt)  # exponential backoff

        print("[Generator] All LLM retries exhausted")
        return None

    # ─────────────────────────────────────────────────
    # UTILITIES
    # ─────────────────────────────────────────────────

    def _clean_llm_output(self, text: str) -> str:
        """
        Strips markdown wrappers and conversational filler from LLM output.
        Tries multiple extraction strategies.
        """
        if not text: return ""
        
        # 1. JSON block
        json_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if json_match:
            return json_match.group(1).strip()

        # 2. Python block
        py_match = re.search(r"```python\s*(.*?)\s*```", text, re.DOTALL)
        if py_match:
            return py_match.group(1).strip()

        # 3. Any code block
        any_match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
        if any_match:
            return any_match.group(1).strip()

        # 4. Raw text fallback
        return text.strip()

    def _save_tool(self, tool_name: str, code: str) -> bool:
        """Saves generated code to the tools/generated/ directory."""
        try:
            filepath = os.path.join(GENERATED_TOOLS_DIR, f"{tool_name}.py")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f'"""\nAuto-generated tool: {tool_name}\nDo not edit manually.\n"""\n\n')
                f.write(code)
            return True
        except Exception as e:
            print(f"[Generator] Save error: {e}")
            return False


# ─────────────────────────────────────────────────────
# GLOBAL INSTANCE
# Registry is injected later to avoid circular imports:
#
# Usage in main.py:
#   from tools.registry  import registry
#   from tools.generator import generator
#   generator.registry = registry   ← inject here
# ─────────────────────────────────────────────────────

generator = ToolGenerator()
