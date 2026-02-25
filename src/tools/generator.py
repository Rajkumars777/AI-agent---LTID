"""
generator.py
============
Auto-generates new Python tools for unknown tasks using LLM.
Includes: safety validation, syntax checking, retry logic, dry-run support.

Also contains DynamicS1Automation — fully dynamic S1-Grade execution engine.
"""

import os
import ast
import json
import re
import asyncio
import time
import hashlib
import logging
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path

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
You are an expert Windows Desktop Automation code generator.
Write a production-grade Python executor for this tool.

═══════════════════════════════════════════════════════════
TASK
═══════════════════════════════════════════════════════════
Tool name: {name}
Description: {description}
Parameters: {params}
Example task: "{query}"

═══════════════════════════════════════════════════════════
API REFERENCE (already in namespace — DO NOT import these)
═══════════════════════════════════════════════════════════

desktop                              # DesktopAutomation instance
  .open_application(name: str)       # Opens app via Start Menu
  .focus_window(title: str)          # Brings existing window to front
  .close_application(name: str)      # Closes app

wait_for_window(title, timeout=15)   # S1-grade: polls OS until window is
                                     # 'active ready'. Returns True/False.
                                     # Replaces time.sleep() for app loading.

pyautogui                            # Mouse & keyboard control
  .press(key)                        # Single key: "enter", "tab", "escape"
  .hotkey("ctrl", "c")               # Combo keys
  .click(x, y)                       # Click at coordinates
  .typewrite("text", interval=0.05)  # Type ASCII only (no unicode)

pyperclip                            # Clipboard (handles unicode)
  .copy(text)                        # Copy to clipboard

gw                                   # pygetwindow (window queries)
  .getActiveWindow()                 # Returns active window
  .getWindowsWithTitle(title)        # Find windows by title

time, os, psutil, subprocess         # Standard libraries

═══════════════════════════════════════════════════════════
RULES
═══════════════════════════════════════════════════════════

1. FUNCTION: def execute(params: dict) -> str
   Must return "[Success] ..." or "[Error] ..."

2. OPEN + VERIFY PATTERN (mandatory after launching any app):
   desktop.open_application("AppName")
   if not wait_for_window("AppName", timeout=15):
       return "[Error] AppName did not open"
   time.sleep(0.5)  # brief UI settle

3. TYPING (always use clipboard for reliability):
   pyperclip.copy(text)
   pyautogui.hotkey("ctrl", "v")

4. BETWEEN ACTIONS: use time.sleep(0.3) to time.sleep(0.5) for
   UI settle. This is OK and necessary.

5. NAVIGATING FIELDS: use pyautogui.press("tab") to move between
   input fields. Use pyautogui.press("escape") to dismiss dialogs.

6. SAFETY: No file deletion, no formatting, no dangerous shell ops.

═══════════════════════════════════════════════════════════
❌ FORBIDDEN (code will be rejected if these appear)
═══════════════════════════════════════════════════════════

- time.sleep(3) or time.sleep(5) to wait for app loading
- Polling loops like: for _ in range(N): time.sleep(1)
- Importing pyautogui, pyperclip, gw (already in namespace)
- os.remove, shutil.rmtree, eval(), exec()

═══════════════════════════════════════════════════════════
APP KEYBOARD SHORTCUTS (use these, don't click blindly)
═══════════════════════════════════════════════════════════

WhatsApp Desktop:
  Ctrl+F         → Open search bar
  Down/Enter     → Select search result (Down to highlight, Enter to open)
  Escape         → Close search / return to chat list
  "Type a message" box auto-focuses after selecting a contact
  Enter          → Send typed message

Notepad:
  Ctrl+N → New file    Ctrl+S → Save    Ctrl+O → Open
  Ctrl+A → Select all  Just start typing — it auto-focuses

Chrome / Edge / Brave:
  Ctrl+L → Focus address bar  Ctrl+T → New tab
  Ctrl+W → Close tab          Ctrl+F → Find on page
  Enter  → Navigate to URL in address bar

Windows Mail / Outlook:
  Ctrl+N → New mail    Tab → Move between To/Subject/Body
  Ctrl+Enter → Send    Ctrl+S → Save draft

File Explorer:
  Win+E → Open          Ctrl+L → Focus address bar
  Enter → Open selected file/folder

General:
  Win → Start Menu      Alt+F4 → Close window
  Alt+Tab → Switch window

═══════════════════════════════════════════════════════════
EXAMPLE 1: Open app and perform action
═══════════════════════════════════════════════════════════

def execute(params: dict) -> str:
    try:
        app = params.get("app_name", "Notepad")
        text = params.get("text", "Hello World")

        # 1. Open and verify
        desktop.open_application(app)
        if not wait_for_window(app, timeout=15):
            return f"[Error] {{app}} did not open within 15s"
        time.sleep(0.5)

        # 2. Type via clipboard
        pyperclip.copy(text)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.3)

        return f"[Success] Typed '{{text}}' in {{app}}"
    except Exception as e:
        return f"[Error] {{str(e)}}"

═══════════════════════════════════════════════════════════
EXAMPLE 2: Multi-step with field navigation
═══════════════════════════════════════════════════════════

def execute(params: dict) -> str:
    try:
        url = params.get("url", "https://google.com")

        # 1. Open Chrome and verify
        desktop.open_application("Chrome")
        if not wait_for_window("Chrome", timeout=15):
            return "[Error] Chrome did not open"
        time.sleep(0.5)

        # 2. Focus address bar and navigate
        pyautogui.hotkey("ctrl", "l")
        time.sleep(0.3)
        pyperclip.copy(url)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.2)
        pyautogui.press("enter")
        time.sleep(2.0)  # Wait for page load

        return f"[Success] Navigated to {{url}}"
    except Exception as e:
        return f"[Error] {{str(e)}}"

═══════════════════════════════════════════════════════════
EXAMPLE 3: Open browser → Navigate to Gmail → Send email
═══════════════════════════════════════════════════════════

def execute(params: dict) -> str:
    try:
        browser = params.get("browser", "brave browser")
        recipient = params.get("recipient", "someone@gmail.com")
        message = params.get("message", "Hello")

        # 1. Open browser and verify
        desktop.open_application(browser)
        if not wait_for_window(browser.split()[0], timeout=15):
            return f"[Error] {{browser}} did not open within 15s"
        time.sleep(1.0)

        # 2. Navigate to Gmail
        pyautogui.hotkey("ctrl", "l")
        time.sleep(0.3)
        pyperclip.copy("https://mail.google.com")
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.3)
        pyautogui.press("enter")
        time.sleep(3.0)  # Wait for Gmail to load

        # 3. Compose (Gmail shortcut: press 'c' to compose)
        pyautogui.press("c")
        time.sleep(2.0)

        # 4. Type recipient
        pyperclip.copy(recipient)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.3)
        pyautogui.press("tab")
        time.sleep(0.3)

        # 5. Type subject
        pyperclip.copy("Hello")
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.3)
        pyautogui.press("tab")
        time.sleep(0.3)

        # 6. Type body and send
        pyperclip.copy(message)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.3)
        pyautogui.hotkey("ctrl", "enter")
        time.sleep(1.0)

        return f"[Success] Email sent to {{recipient}} via Gmail"
    except Exception as e:
        return f"[Error] {{str(e)}}"

═══════════════════════════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════════════════════════

Return ONLY raw Python code. No markdown. No ``` blocks.
The code MUST define execute(params) -> str.
"""


# ─────────────────────────────────────────────────────
# TOOL GENERATOR
# ─────────────────────────────────────────────────────

class ToolGenerator:
    """
    Generates new Python tools for unknown tasks.
    Uses LLM to create both the schema and executor code.
    """

    def __init__(self):
        self._provider = "groq"
        self._model = "llama-3.3-70b-versatile"
        self._client = None
        self.registry = None   # injected from main.py

        os.makedirs(GENERATED_TOOLS_DIR, exist_ok=True)

    @property
    def client(self):
        if self._client:
            return self._client
        if self._provider == "groq":
            api_key = os.getenv("GROQ_API_KEY")
            if api_key:
                self._client = Groq(api_key=api_key)
                return self._client
        if self._provider == "openrouter":
            from openai import OpenAI
            api_key = os.getenv("OPENROUTER_API_KEY")
            if api_key:
                self._client = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=api_key,
                )
                return self._client
        raise ValueError("No LLM API key found. Set GROQ_API_KEY or OPENROUTER_API_KEY.")

    # ─── Safety ──────────────────────────────────────

    def is_safe_code(self, code: str) -> tuple:
        """Returns (True, None) if safe, (False, pattern) if dangerous."""
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, code, re.IGNORECASE):
                return False, pattern
        return True, None

    # ─── LLM Call ────────────────────────────────────

    async def _call_llm_with_retry(
        self,
        prompt: str,
        reasoning_effort: str = "low",
        temperature: float    = 0.2,
        retries: int          = 3,
        delay: float          = 1.5
    ) -> str | None:
        """
        Calls LLM (Groq or OpenRouter) with automatic retry and provider-switching.
        Handles rate limits by falling back to secondary provider.
        """
        for attempt in range(1, retries + 1):
            try:
                model = self._model if self._provider == "openrouter" else "llama-3.3-70b-versatile"

                response = self.client.chat.completions.create(
                    model       = model,
                    messages    = [{"role": "user", "content": prompt}],
                    temperature = temperature,
                    max_tokens  = 2048,
                )
                return response.choices[0].message.content

            except Exception as e:
                err_msg = str(e).lower()
                print(f"[Generator] LLM attempt {attempt}/{retries} ({self._provider}) failed: {e}")

                # Switch provider if rate limited (429)
                if "rate_limit_exceeded" in err_msg or "429" in err_msg:
                    if self._provider == "groq" and os.getenv("OPENROUTER_API_KEY"):
                        print("[Generator] 🚨 Groq Rate Limit! Switching to OpenRouter...")
                        self._provider = "openrouter"
                        self._model = "google/gemini-2.0-flash-001"
                        self._client = None  # Force re-init
                    elif self._provider == "openrouter" and os.getenv("GROQ_API_KEY"):
                        print("[Generator] 🚨 OpenRouter Issue! Switching to Groq...")
                        self._provider = "groq"
                        self._client = None

                if attempt < retries:
                    await asyncio.sleep(delay * attempt)

        print("[Generator] All LLM retries exhausted")
        return None

    # ─── Code Cleaning ───────────────────────────────

    def _clean_llm_output(self, text: str) -> str:
        """
        Strips markdown wrappers and conversational filler from LLM output.
        """
        if not text:
            return ""

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

    # ─── Generation Pipeline ─────────────────────────

    async def _generate_definition(self, query: str) -> dict | None:
        """Ask LLM to generate a tool definition (schema)."""
        prompt = DEFINITION_PROMPT.format(query=query)
        raw = await self._call_llm_with_retry(prompt, reasoning_effort="low")
        if not raw:
            return None

        cleaned = self._clean_llm_output(raw)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            json_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except Exception:
                    pass
        return None

    async def _generate_code(self, tool_def: dict, query: str) -> str | None:
        """Ask LLM to generate the Python executor code."""
        prompt = CODE_PROMPT.format(
            name        = tool_def["name"],
            description = tool_def["description"],
            params      = json.dumps(
                tool_def.get("parameters") or tool_def.get("input_schema", {}).get("properties", {}),
                indent=2
            ),
            query       = query
        )

        raw = await self._call_llm_with_retry(prompt, reasoning_effort="medium", temperature=0.2)
        if not raw:
            return None

        code = self._clean_llm_output(raw)

        # Syntax check
        try:
            ast.parse(code)
        except SyntaxError as e:
            print(f"[Generator] Syntax error in generated code: {e}")
            return None

        # Safety check
        safe, blocked = self.is_safe_code(code)
        if not safe:
            print(f"[Generator] ⛔ Unsafe code blocked: '{blocked}'")
            return None

        return code

    async def _extract_values(self, tool_def: dict, query: str) -> dict:
        """Ask LLM to extract parameter values from the user query."""
        properties = tool_def.get("input_schema", {}).get("properties", {})
        if not properties:
            return {}

        prompt = f"""
Extract parameter values from this user request for the tool "{tool_def['name']}".

Tool parameters:
{json.dumps(properties, indent=2)}

User request: "{query}"

Return ONLY a JSON object with parameter names as keys and extracted values as strings.
If a parameter isn't mentioned, use an empty string "".
Example: {{"contact": "AKKA", "message": "hello"}}
"""
        raw = await self._call_llm_with_retry(prompt, reasoning_effort="low", temperature=0.1)
        if not raw:
            return {}

        cleaned = self._clean_llm_output(raw)
        try:
            return json.loads(cleaned)
        except Exception:
            try:
                json_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(0))
            except Exception:
                pass
        return {}

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
# GLOBAL GENERATOR INSTANCE
# Registry is injected later to avoid circular imports:
#   from src.tools.registry  import registry
#   from src.tools.generator import generator
#   generator.registry = registry
# ─────────────────────────────────────────────────────

generator = ToolGenerator()


# ─────────────────────────────────────────────────────
# DYNAMIC S1-GRADE AUTOMATION
# ─────────────────────────────────────────────────────
# Fully dynamic: LLM generates code for ANY task.
# No hardcoded examples. Caches successful code.
# ─────────────────────────────────────────────────────

import pyautogui
import pyperclip
import pygetwindow as gw

try:
    from pywinauto.application import Application
    PYWINAUTO_AVAILABLE = True
except ImportError:
    PYWINAUTO_AVAILABLE = False

_logger = logging.getLogger(__name__)


S1_CODE_PROMPT = """You are an expert S1-Grade Windows Desktop Automation code generator.

═══ USER TASK ═══
{query}

═══ CRITICAL RULES ═══

1. ALWAYS use params.get("key", "default") — NEVER params["key"] directly.
   The params dict may not have every key. Using params["key"] causes KeyError.

2. NEVER use blind time.sleep() to wait for apps to load.
   ALWAYS use wait_for_window() after opening any app.

3. Pattern for opening apps:
   desktop.open_application("AppName")
   if not wait_for_window("AppName", timeout=15):
       return "[Error] AppName did not open"
   time.sleep(0.5)  # brief UI settle only

4. OPEN IN NEW TAB — when navigating to any URL in a browser, ALWAYS open a
   new tab first so you don't replace the agent's own page:
   pyautogui.hotkey("ctrl", "t")   # new tab
   time.sleep(0.5)
   pyautogui.hotkey("ctrl", "l")   # focus address bar
   ...navigate as normal...

5. TYPING — always use clipboard for reliability:
   pyperclip.copy(text)
   pyautogui.hotkey('ctrl', 'v')

6. Between UI actions: time.sleep(0.3) to time.sleep(1.0) for settle.

7. Use keyboard shortcuts, not mouse clicks when possible.

═══ AVAILABLE IN NAMESPACE (DO NOT import) ═══

desktop                              # DesktopAutomation instance
  .open_application(name: str)       # Opens app via Start Menu
  .focus_window(title: str)          # Brings window to front
  .close_application(name: str)      # Closes app

wait_for_window(title, timeout=15)   # S1-Grade: polls OS until window active
                                     # Returns True/False. Replaces sleep().

pyautogui                            # Mouse & keyboard
  .press(key)                        # "enter", "tab", "escape", "down"
  .hotkey("ctrl", "c")               # Combo keys
  .click(x, y)                       # Click at coordinates
  .typewrite("text", interval=0.05)  # Type ASCII only

pyperclip                            # Clipboard (unicode safe)
  .copy(text)

gw                                   # pygetwindow
  .getActiveWindow()
  .getWindowsWithTitle(title)

time, os                             # Standard libs

═══ APP KEYBOARD SHORTCUTS ═══

WhatsApp Desktop:
  Ctrl+F → Search bar | Down+Enter → Select result
  Message box auto-focuses after selecting contact
  Enter → Send message | Escape → Close search

Chrome / Brave / Edge:
  Ctrl+T → New tab (ALWAYS use first when navigating!)
  Ctrl+L → Address bar | Enter → Navigate

Gmail (in browser — after page loads):
  'c' (lowercase c) → Opens compose window
  To field auto-focuses | Tab → Subject | Tab → Body
  Ctrl+Enter → Send email

Notepad:
  Auto-focuses text area on open
  Ctrl+S → Save | Ctrl+N → New

Windows Mail:
  Ctrl+N → New mail | Tab → Between fields
  Ctrl+Enter → Send

═══ PARAMS (always use .get() with a default) ═══

  params.get("contact", "")              - person name
  params.get("message", "")              - message/body text
  params.get("recipient", "")            - email address
  params.get("subject", "No Subject")    - email subject
  params.get("body", "")                 - email body
  params.get("browser", "Brave")         - browser name
  params.get("url", "https://mail.google.com") - URL
  params.get("app", "")                  - app name
  params.get("text", "")                 - generic text

═══ GMAIL COMPOSE TEMPLATE (use this exact pattern for email tasks) ═══

def execute(params: dict) -> str:
    try:
        browser   = params.get("browser", "Brave")
        recipient = params.get("recipient", "")
        subject   = params.get("subject", "No Subject")
        body      = params.get("body", params.get("message", ""))

        # 1. Open / focus browser
        desktop.open_application(browser)
        if not wait_for_window(browser, timeout=15):
            return f"[Error] {{browser}} did not open"
        time.sleep(0.8)

        # 2. NEW TAB — prevents replacing agent page
        pyautogui.hotkey("ctrl", "t")
        time.sleep(0.5)

        # 3. Navigate to Gmail
        pyautogui.hotkey("ctrl", "l")
        time.sleep(0.3)
        pyperclip.copy("https://mail.google.com")
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.2)
        pyautogui.press("enter")
        time.sleep(4.0)   # wait for Gmail to fully load

        # 4. Open compose window (Gmail shortcut)
        pyautogui.press("c")
        time.sleep(2.5)   # wait for compose dialog

        # 5. To field (auto-focused)
        pyperclip.copy(recipient)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.5)
        pyautogui.press("tab")   # → Subject
        time.sleep(0.3)

        # 6. Subject
        pyperclip.copy(subject)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.3)
        pyautogui.press("tab")   # → Body
        time.sleep(0.3)

        # 7. Body
        pyperclip.copy(body)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.3)

        # 8. Send
        pyautogui.hotkey("ctrl", "enter")
        time.sleep(1.5)

        return f"[Success] Email sent to {{recipient}} via Gmail"
    except Exception as e:
        return f"[Error] {{str(e)}}"

═══ OUTPUT ═══

Return ONLY raw Python code. No markdown. No explanation. No ``` blocks.
MUST define: def execute(params: dict) -> str
MUST return "[Success] ..." or "[Error] ..."
"""


class DynamicS1Automation:
    """
    Fully dynamic S1-Grade automation.
    Uses LLM to generate code for ANY task. No hardcoded examples.
    Caches successful code for instant reuse.
    """

    def __init__(self):
        self.cache_dir = Path(GENERATED_TOOLS_DIR).parent / "s1_cache"
        self.cache_dir.mkdir(exist_ok=True)

    # ─────────────────────────────────────
    # PUBLIC: Main entry point
    # ─────────────────────────────────────

    # Keywords that indicate a web/browser task → use Playwright
    _WEB_KEYWORDS = [
        "gmail", "google", "youtube", "github", "amazon", "website", "webpage",
        "browser", "chrome", "brave", "edge", "firefox", "search online",
        "navigate to", "go to", "open url", "http", "www.", ".com",
        "web", "email via", "send email", "compose email",
    ]

    def _is_web_task(self, query: str) -> bool:
        q = query.lower()
        return any(k in q for k in self._WEB_KEYWORDS)

    async def execute_task(self, query: str, emit=None) -> Dict[str, Any]:
        """
        Executes ANY task dynamically.

        Browser/web tasks → Playwright (BrowserAgent via web_automation)
        Desktop tasks    → LLM-generated pyautogui code (S1-Grade)
        """
        _logger.info(f"[DynamicS1] Task: {query}")

        try:
            # ── Route web tasks to Playwright BrowserAgent ──────────
            if self._is_web_task(query):
                _logger.info("[DynamicS1] 🌐 Web task detected → using BrowserAgent (Playwright)")
                from src.services.browser.intelligent_web_automation import web_automation
                if emit:
                    await emit("AgentStep", {"desc": f"🌐 Running Web Task: {query}"})
                results_list = await web_automation.perform_action(query)
                joined_results = "\n".join(results_list)
                success = "❌" not in joined_results
                return {"success": success, "result": joined_results, "method": "intelligent_web_automation"}

            # ── Desktop tasks: check cache first ────────────────────
            cached_code = self._get_cached(query)

            if cached_code:
                _logger.info("[DynamicS1] ⚡ Using cached code")
                if emit:
                    await emit("AgentStep", {"desc": "⚡ Using cached automation code..."})
                code = cached_code
                method = "cached"
            else:
                if emit:
                    await emit("AgentStep", {"desc": f"🧠 Generating S1-Grade automation for: '{query}'"})

                code = await self._generate_code(query)
                if not code:
                    return {"success": False, "result": "❌ Code generation failed", "method": "failed"}

                _logger.info(f"[DynamicS1] Generated code ({len(code)} chars)")
                method = "generated"

            # Step 3: Validate
            is_valid, issues = self._validate_code(code)
            if not is_valid:
                _logger.warning(f"[DynamicS1] Validation issues: {issues}")

            # Step 4: Execute
            if emit:
                await emit("AgentStep", {"desc": "🚀 Executing automation..."})

            params = self._extract_params(query)
            result = self._execute(code, params)

            # Step 5: Cache if successful
            if "[Success]" in result and method != "cached":
                self._cache(query, code)
                _logger.info("[DynamicS1] ✅ Cached for reuse")

            success = "[Success]" in result
            return {"success": success, "result": result, "method": method}

        except Exception as e:
            _logger.error(f"[DynamicS1] Error: {e}")
            return {"success": False, "result": f"❌ Error: {e}", "method": "error"}

    # ─────────────────────────────────────
    # LLM CODE GENERATION
    # ─────────────────────────────────────

    async def _generate_code(self, query: str) -> Optional[str]:
        """Generates S1-Grade Python code using the existing generator's LLM."""
        prompt = S1_CODE_PROMPT.format(query=query)

        # Reuse generator's LLM client and retry logic
        raw = await generator._call_llm_with_retry(
            prompt=prompt, temperature=0.2, retries=3
        )

        if not raw:
            return None

        code = generator._clean_llm_output(raw)

        if code and "def execute" in code:
            return code

        _logger.warning("[DynamicS1] Generated code missing execute()")
        return None

    # ─────────────────────────────────────
    # VALIDATION
    # ─────────────────────────────────────

    def _validate_code(self, code: str) -> tuple:
        """Validates code follows S1-Grade patterns."""
        issues = []

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, [f"Syntax error: {e}"]

        has_execute = any(
            isinstance(n, ast.FunctionDef) and n.name == "execute"
            for n in ast.walk(tree)
        )
        if not has_execute:
            issues.append("No execute() function")

        if "desktop.open_application" in code and "wait_for_window" not in code:
            issues.append("Opens app without wait_for_window()")

        for m in re.finditer(r"time\.sleep\((\d+(?:\.\d+)?)\)", code):
            if float(m.group(1)) >= 3.0:
                issues.append(f"Forbidden blind sleep: time.sleep({m.group(1)})")

        safe, blocked = generator.is_safe_code(code)
        if not safe:
            issues.append(f"Dangerous pattern: {blocked}")

        is_valid = len(issues) == 0 or (
            len(issues) == 1 and "wait_for_window" in issues[0]
        )
        return is_valid, issues

    # ─────────────────────────────────────
    # EXECUTION
    # ─────────────────────────────────────

    def _execute(self, code: str, params: dict) -> str:
        """Executes generated code with S1-Grade helpers injected."""
        try:
            from src.services.desktop.automation import desktop_automation

            def wait_for_window(title: str, timeout: float = 15.0) -> bool:
                """S1-Grade: poll OS until window is active."""
                if PYWINAUTO_AVAILABLE:
                    try:
                        title_re = f".*{re.escape(title)}.*"
                        conn = Application(backend="uia").connect(
                            title_re=title_re, timeout=int(timeout)
                        )
                        win = conn.window(title_re=title_re)
                        win.wait("active ready", timeout=int(timeout))
                        _logger.info(f"[S1] ✅ '{title}' is ready")
                        return True
                    except Exception as e:
                        _logger.warning(f"[S1] pywinauto wait failed: {e}")

                # Fallback: pygetwindow
                deadline = time.time() + timeout
                while time.time() < deadline:
                    try:
                        wins = gw.getWindowsWithTitle(title)
                        if wins:
                            return True
                        active = gw.getActiveWindow()
                        if active and title.lower() in active.title.lower():
                            return True
                    except Exception:
                        pass
                    time.sleep(0.5)
                return False

            namespace = {
                "desktop": desktop_automation,
                "wait_for_window": wait_for_window,
                "pyautogui": pyautogui,
                "pyperclip": pyperclip,
                "gw": gw,
                "time": time,
                "os": os,
                "params": params,
            }

            exec(compile(ast.parse(code), "<dynamic_s1>", "exec"), namespace)

            execute_fn = namespace.get("execute")
            if not execute_fn or not callable(execute_fn):
                return "[Error] No execute() function in generated code"

            return execute_fn(params)

        except Exception as e:
            import traceback
            _logger.error(f"[DynamicS1] Execution error:\n{traceback.format_exc()}")
            return f"[Error] Execution failed: {e}"

    # ─────────────────────────────────────
    # PARAMETER EXTRACTION
    # ─────────────────────────────────────

    def _extract_params(self, query: str) -> Dict[str, Any]:
        """Extracts parameters from natural language query."""
        params = {}
        q = query.lower()

        # Quoted text → message/body
        quotes = re.findall(r"['\"]([^'\"]+)['\"]", query)
        if quotes:
            params["message"] = quotes[0]
            params["body"] = quotes[0]
            if len(quotes) > 1:
                params["subject"] = quotes[1]

        # "to NAME" → contact or recipient
        to_match = re.search(r"\bto\s+(\S+)", query, re.IGNORECASE)
        if to_match:
            val = to_match.group(1).strip("'\"")
            if "@" in val:
                params["recipient"] = val
            else:
                params["contact"] = val

        # App detection
        app_map = {
            "whatsapp": "WhatsApp", "chrome": "Chrome",
            "brave": "Brave", "edge": "Edge",
            "firefox": "Firefox", "notepad": "Notepad",
            "gmail": "Gmail", "outlook": "Outlook",
            "excel": "Excel", "word": "Word",
            "spotify": "Spotify",
        }
        for key, name in app_map.items():
            if key in q:
                params["app"] = name
                break

        # Browser detection
        browsers = {"brave": "Brave", "chrome": "Chrome", "edge": "Edge", "firefox": "Firefox"}
        for key, name in browsers.items():
            if key in q:
                params["browser"] = name
                break

        # URL detection
        url_match = re.search(
            r"(?:go to|navigate to|open)\s+([\w\.-]+\.(?:com|org|net|io)[^\s]*)",
            query, re.IGNORECASE
        )
        if url_match:
            params["url"] = url_match.group(1)

        # Gmail → always set url
        if "gmail" in q and "url" not in params:
            params["url"] = "https://mail.google.com"

        # Generic text after "type" / "write"
        type_match = re.search(
            r"(?:type|write|enter)\s+['\"]?(.+?)['\"]?\s*(?:in|on|$)", query, re.IGNORECASE
        )
        if type_match:
            params["text"] = type_match.group(1).strip("'\"")

        return params

    # ─────────────────────────────────────
    # CACHING
    # ─────────────────────────────────────

    def _cache_key(self, query: str) -> str:
        normalized = re.sub(r"['\"]", "", query.lower().strip())
        normalized = re.sub(r"\s+", " ", normalized)
        return hashlib.md5(normalized.encode()).hexdigest()

    def _get_cached(self, query: str) -> Optional[str]:
        cache_file = self.cache_dir / f"{self._cache_key(query)}.py"
        if cache_file.exists():
            code = cache_file.read_text(encoding="utf-8")
            if '"""' in code:
                parts = code.split('"""')
                if len(parts) >= 3:
                    return '"""'.join(parts[2:]).strip()
            return code
        return None

    def _cache(self, query: str, code: str):
        cache_file = self.cache_dir / f"{self._cache_key(query)}.py"
        cache_file.write_text(
            f'"""\nCached S1-Grade code for: {query}\nGenerated: {time.strftime("%Y-%m-%d %H:%M")}\n"""\n\n{code}',
            encoding="utf-8",
        )


# ─────────────────────────────────────────────────────
# GLOBAL DYNAMIC S1 INSTANCE
# ─────────────────────────────────────────────────────

dynamic_s1_automation = DynamicS1Automation()
