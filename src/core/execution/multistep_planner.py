"""
src/core/execution/multistep_planner.py
========================================
Decomposes complex natural language queries into ordered action steps.

The LLM converts a query like:
  "open gmail and send hello to raj@gmail.com"
into:
  [
    {"action": "OPEN",        "target": "gmail",           "context": None,            "description": "Open Gmail in browser"},
    {"action": "WEB_CONTROL", "target": "compose email",   "context": "raj@gmail.com", "description": "Compose new email to raj@gmail.com"},
    {"action": "TYPE_DESKTOP","target": "hello",           "context": None,            "description": "Type the email body"},
    {"action": "WEB_CONTROL", "target": "send email",      "context": None,            "description": "Click Send"},
  ]

Each step maps directly to an action that handle_action() already knows.
"""

import json
import re
import os
from typing import List, Optional
from dataclasses import dataclass, field


# ─────────────────────────────────────────────────────────────────────────────
# DATA MODELS
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PlanStep:
    """A single executable step in a multi-step plan."""
    step_number:  int
    action:       str            # Must match a handle_action() action key
    target:       str            # Primary target (app name, file, URL, text)
    context:      Optional[str]  # Secondary param (destination, new_name, etc.)
    description:  str            # Human-readable description shown in UI
    depends_on:   Optional[str] = None   # Key from a previous step's output to inject
    output_key:   Optional[str] = None   # Key to store this step's result under


@dataclass
class MultiStepPlan:
    """A complete decomposed plan for a complex query."""
    original_query: str
    steps:          List[PlanStep]
    intent:         str           # e.g. "send_email", "whatsapp_message", "stock_to_excel"
    is_multistep:   bool = True


# ─────────────────────────────────────────────────────────────────────────────
# KNOWN MULTI-STEP PATTERNS  (fast path — no LLM needed for common cases)
# ─────────────────────────────────────────────────────────────────────────────

def _try_pattern_match(query: str) -> Optional[MultiStepPlan]:
    """
    Match common multi-step patterns directly without LLM call.
    Returns a plan if matched, None if LLM is needed.
    """
    q = query.lower().strip()

    # ── Pattern: Send WhatsApp message ───────────────────────────────────────
    # ONLY match when "whatsapp" is explicitly in the query
    # "send hi to AKKA on whatsapp" / "whatsapp hello to John"
    if "whatsapp" in q:
        wa_match = re.search(
            r'(?:send|message|msg)\s+["\']?(.+?)["\']?\s+(?:to|for)\s+(.+?)(?:\s+(?:on|via|through|in)\s+whatsapp)?$',
            query, re.IGNORECASE
        )
        if wa_match or ("send" in q or "message" in q or "msg" in q):
            # Extract message and contact
            msg_match = re.search(r'["\']([^"\']+)["\']', query)
            contact_match = re.search(
                r'(?:to|for)\s+([A-Za-z][A-Za-z\s]+?)(?:\s+(?:on|via|in|through)\s+whatsapp|$)',
                query, re.IGNORECASE
            )
            message = msg_match.group(1) if msg_match else (wa_match.group(1).strip() if wa_match else "hi")
            contact = contact_match.group(1).strip() if contact_match else (wa_match.group(2).strip() if wa_match else "")

            if contact:
                return MultiStepPlan(
                    original_query=query,
                    intent="whatsapp_message",
                    steps=[
                        PlanStep(1, "OPEN",                  "whatsapp", None,    "Open WhatsApp"),
                        PlanStep(2, "send_whatsapp_message",  contact,   message, f"Send '{message}' to {contact}"),
                    ]
                )

    # ── Pattern: Send Email ───────────────────────────────────────────────────
    # "open email and send hello to raj@gmail.com"
    # "send mail with subject Test and body Hello to raj@gmail.com"
    email_match = re.search(r'[\w.+-]+@[\w-]+\.\w+', query)
    if email_match and ("send" in q or "mail" in q or "email" in q):
        recipient = email_match.group(0)
        
        subject_match = re.search(r'subject\s+["\']?([^"\']+?)["\']?(?:\s+and|\s+body|$)', query, re.IGNORECASE)
        body_match    = re.search(r'body\s+["\']?([^"\']+?)["\']?(?:\s+to\s+|$)',           query, re.IGNORECASE)
        msg_match     = re.search(r'["\']([^"\']+)["\']', query)
        
        subject = subject_match.group(1).strip() if subject_match else "Hello"
        body    = body_match.group(1).strip()    if body_match    else (msg_match.group(1) if msg_match else "Hello")

        return MultiStepPlan(
            original_query=query,
            intent="send_email",
            steps=[
                PlanStep(1, "send_email", recipient, f"{subject}|{body}",
                         f"Send email to {recipient} with subject '{subject}'"),
            ]
        )

    # ── Pattern: Stock data → Excel ──────────────────────────────────────────
    # "get Apple stock price and save to excel with column stock price"
    # "extract Microsoft stock and store in new excel file"
    stock_keywords = ["stock", "share price", "market price", "closing price"]
    excel_keywords = ["excel", "spreadsheet", "xlsx", ".xlsx", "save to", "store in"]
    
    has_stock = any(kw in q for kw in stock_keywords)
    has_excel = any(kw in q for kw in excel_keywords)

    if has_stock and has_excel:
        # Extract company name
        company_match = re.search(
            r'(?:of|for|about|get|fetch|extract)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+stock',
            query, re.IGNORECASE
        )
        # Extract column name
        col_match = re.search(
            r'column\s+(?:name\s+)?["\']?([^"\']+?)["\']?(?:\s*$|\s+and)',
            query, re.IGNORECASE
        )
        # Extract file name
        file_match = re.search(r'["\']?([A-Za-z0-9_\-\s]+\.xlsx)["\']?', query, re.IGNORECASE)

        company    = company_match.group(1).strip() if company_match else "Apple"
        col_name   = col_match.group(1).strip()     if col_match     else "Stock Price"
        excel_file = file_match.group(1).strip()    if file_match    else f"{company.lower()}_stock.xlsx"

        task_desc = f"Fetch current {company} stock price and create Excel file '{excel_file}' with column '{col_name}' containing the price value"

        return MultiStepPlan(
            original_query=query,
            intent="stock_to_excel",
            steps=[
                PlanStep(1, "DYNAMIC_CODE", excel_file, task_desc,
                         f"Fetch {company} stock price and save to {excel_file}",
                         output_key="excel_path"),
            ]
        )

    # ── Pattern: Open app + do something ─────────────────────────────────────
    # "open spotify and play music" / "open notepad and type hello world"
    # "open brave browser and search gmail and send mail hi to rajcsecs"
    open_and_match = re.search(
        r'open\s+(.+?)\s+and\s+(.+)',
        query, re.IGNORECASE
    )
    if open_and_match:
        app_raw = open_and_match.group(1).strip()
        rest    = open_and_match.group(2).strip()

        # Clean app name — remove filler words like "the", "app", "application"
        app = re.sub(r'\b(the|app|application)\b', '', app_raw, flags=re.IGNORECASE).strip()

        steps = [PlanStep(1, "OPEN", app, None, f"Open {app}")]
        step_num = 2

        # Split remaining actions on " and " to handle compound chains
        # e.g. "search gmail and send mail hi to rajcsecs"
        sub_actions = re.split(r'\s+and\s+', rest, flags=re.IGNORECASE)

        for sub_action in sub_actions:
            sub_lower = sub_action.lower().strip()

            if any(kw in sub_lower for kw in ["type", "write", "enter"]):
                text_match = re.search(r'["\']([^"\']+)["\']', sub_action)
                text = text_match.group(1) if text_match else re.sub(
                    r'^(?:type|write|enter)\s+', '', sub_action, flags=re.IGNORECASE
                ).strip()
                steps.append(PlanStep(step_num, "TYPE_DESKTOP", text, None, f"Type '{text}'"))
                step_num += 1

            elif any(kw in sub_lower for kw in ["search", "go to", "navigate", "open"]):
                # Extract what to search/navigate to
                text_match = re.search(
                    r'(?:search|go\s+to|navigate\s+to|open)\s+["\']?(.+?)["\']?\s*$',
                    sub_action, re.IGNORECASE
                )
                text = text_match.group(1).strip() if text_match else sub_action

                # Check if it's a known site — use browser navigation
                site_map = {
                    "gmail": "https://mail.google.com",
                    "google": "https://www.google.com",
                    "youtube": "https://www.youtube.com",
                    "github": "https://github.com",
                    "amazon": "https://www.amazon.in",
                }
                url = site_map.get(text.lower())
                if url:
                    steps.append(PlanStep(step_num, "WEB_CONTROL", f"navigate to {text}", url, f"Go to {text}"))
                else:
                    steps.append(PlanStep(step_num, "TYPE_DESKTOP", text, None, f"Search for '{text}'"))
                    step_num += 1
                    steps.append(PlanStep(step_num, "PRESS_KEY", "enter", None, "Press Enter"))
                step_num += 1

            elif any(kw in sub_lower for kw in ["send mail", "send email", "email", "mail"]):
                # Email sending: extract recipient and message
                email_match = re.search(r'[\w.+-]+@[\w-]+\.\w+', sub_action)
                msg_match = re.search(r'(?:send\s+(?:mail|email)\s+)(.*?)(?:\s+to\s+|\s*$)', sub_action, re.IGNORECASE)
                recipient = email_match.group(0) if email_match else (
                    re.search(r'to\s+(\S+)', sub_action, re.IGNORECASE).group(1) if re.search(r'to\s+(\S+)', sub_action) else ""
                )
                body = msg_match.group(1).strip() if msg_match else "Hello"
                steps.append(PlanStep(step_num, "WEB_CONTROL",
                    f"compose and send email saying '{body}' to {recipient}",
                    None, f"Send email '{body}' to {recipient}"))
                step_num += 1

            elif any(kw in sub_lower for kw in ["click", "press", "tap"]):
                text_match = re.search(r'(?:click|press|tap)\s+["\']?(.+)["\']?', sub_action, re.IGNORECASE)
                text = text_match.group(1).strip() if text_match else sub_action
                steps.append(PlanStep(step_num, "CLICK_TEXT", text, None, f"Click '{text}'"))
                step_num += 1

            else:
                # Generic: treat as a screen agent task
                steps.append(PlanStep(step_num, "ANALYZE_SCREEN_AND_ACT", sub_action, None, sub_action))
                step_num += 1

        if len(steps) > 1:
            return MultiStepPlan(original_query=query, intent="open_and_act", steps=steps)

    return None  # No pattern matched — needs LLM


# ─────────────────────────────────────────────────────────────────────────────
# LLM-BASED PLANNER  (for complex / custom queries)
# ─────────────────────────────────────────────────────────────────────────────

PLANNER_SYSTEM_PROMPT = """You are a Windows desktop automation planner.
Break the user's request into ordered steps. Each step uses ONE action.

═══ AVAILABLE ACTIONS ═══
OPEN            - Open an app or file. target = app name (e.g. "brave browser", "notepad")
CLOSE           - Close an app. target = app name
WEB_CONTROL     - Do something in a browser. target = task description, context = URL (optional)
TYPE_DESKTOP    - Type text via keyboard. target = text to type
CLICK_TEXT      - Click visible text on screen. target = text to click
PRESS_KEY       - Press a key. target = key name (enter, esc, tab, ctrl+c, etc.)
SCROLL          - Scroll. target = number (positive=up, negative=down)
SCREENSHOT      - Take a screenshot
READ_SCREEN     - Read all text on screen via OCR
DYNAMIC_CODE    - Fetch data or run code. target = file path, context = task description
EXCEL_WRITE     - Write to excel. target = file, context = sheet,cell,value
EXCEL_READ      - Read excel. target = file path
ANALYZE_SCREEN_AND_ACT - Autonomous screen interaction. target = task description
send_whatsapp_message  - Send WhatsApp. target = contact, context = message
send_email             - Send email. target = recipient, context = subject|body

═══ KNOWN SITES (use these URLs in context for WEB_CONTROL) ═══
gmail → https://mail.google.com
google → https://www.google.com
youtube → https://www.youtube.com
github → https://github.com
amazon → https://www.amazon.in

═══ EXAMPLES ═══

User: "open brave browser and search gmail and send mail hi to rajcsecs"
{
  "intent": "browser_email",
  "steps": [
    {"step_number": 1, "action": "OPEN", "target": "brave browser", "context": null, "description": "Open Brave browser"},
    {"step_number": 2, "action": "WEB_CONTROL", "target": "navigate to Gmail", "context": "https://mail.google.com", "description": "Go to Gmail"},
    {"step_number": 3, "action": "WEB_CONTROL", "target": "compose and send email saying hi to rajcsecs", "context": null, "description": "Send email hi to rajcsecs"}
  ]
}

User: "send hello to AKKA on whatsapp"
{
  "intent": "whatsapp_message",
  "steps": [
    {"step_number": 1, "action": "OPEN", "target": "whatsapp", "context": null, "description": "Open WhatsApp"},
    {"step_number": 2, "action": "send_whatsapp_message", "target": "AKKA", "context": "hello", "description": "Send hello to AKKA"}
  ]
}

User: "open notepad and type hello world"
{
  "intent": "open_and_type",
  "steps": [
    {"step_number": 1, "action": "OPEN", "target": "notepad", "context": null, "description": "Open Notepad"},
    {"step_number": 2, "action": "TYPE_DESKTOP", "target": "hello world", "context": null, "description": "Type hello world"}
  ]
}

═══ RULES ═══
1. Use ONLY the actions listed above. Do NOT invent new ones.
2. For browser tasks, use WEB_CONTROL with the URL in context.
3. For WhatsApp, ALWAYS use send_whatsapp_message (not TYPE_DESKTOP).
4. For email via browser, use WEB_CONTROL (not send_email which is desktop Mail app).
5. Respond with ONLY valid JSON. No markdown. No explanation. No ```."""


def _plan_with_llm(query: str) -> Optional[MultiStepPlan]:
    """
    Use OpenRouter or Groq LLM to decompose a complex query into steps.
    Direct API call — no DSPy dependency.
    """
    import os
    from dotenv import load_dotenv
    load_dotenv()

    # Build the API client (prefer Gemini, then OpenRouter, fallback to Groq)
    client = None
    model  = None

    gemini_key = os.getenv("GEMINI_API_KEY")
    groq_key   = os.getenv("GROQ_API_KEY")
    or_key     = os.getenv("OPENROUTER_API_KEY")

    if gemini_key:
        try:
            from openai import OpenAI
            client = OpenAI(
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                api_key=gemini_key,
            )
            model = "gemini-2.5-flash"
            print("[Planner] Using Gemini API")
        except Exception:
            pass

    if not client and or_key:
        try:
            from openai import OpenAI
            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=or_key,
            )
            model = "google/gemini-2.0-flash-001"
            print("[Planner] Using OpenRouter API")
        except Exception:
            pass

    if not client and groq_key:
        try:
            from groq import Groq
            client = Groq(api_key=groq_key)
            model  = "llama-3.3-70b-versatile"
            print("[Planner] Using Groq API")
        except Exception:
            pass

    if not client:
        print("[Planner] No API key found for LLM planning")
        return None

    try:
        print(f"[Planner] LLM decomposing: '{query}'")

        response = client.chat.completions.create(
            model       = model,
            messages    = [
                {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
                {"role": "user",   "content": query},
            ],
            temperature = 0.1,
            max_tokens  = 1024,
        )

        raw = response.choices[0].message.content.strip()

        # Strip markdown wrappers if LLM added them
        raw = re.sub(r'^```(?:json)?\s*\n?', '', raw)
        raw = re.sub(r'\n?\s*```$', '', raw)
        raw = raw.strip()

        # Find JSON object in the response
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            raw = json_match.group(0)

        data = json.loads(raw)
        steps = []

        for s in data.get("steps", []):
            steps.append(PlanStep(
                step_number = s.get("step_number", len(steps) + 1),
                action      = s.get("action", "ANSWER"),
                target      = str(s.get("target", "")),
                context     = s.get("context") or None,
                description = s.get("description", ""),
            ))

        if steps:
            plan = MultiStepPlan(
                original_query = query,
                intent         = data.get("intent", "custom"),
                steps          = steps,
            )
            print(f"[Planner] LLM plan: intent='{plan.intent}', {len(steps)} steps")
            for s in steps:
                print(f"  Step {s.step_number}: {s.action} → {s.target!r}")
            return plan

    except json.JSONDecodeError as e:
        print(f"[Planner] JSON parse error: {e}")
        print(f"[Planner] Raw LLM output: {raw[:200]}")
    except Exception as e:
        print(f"[Planner] LLM planning failed: {e}")

        # If Gemini/OpenRouter rate-limited or failed, retry with OpenRouter then Groq
        if or_key and ("rate_limit" in str(e).lower() or "402" in str(e) or "429" in str(e) or "error" in str(e).lower()):
            print("[Planner] Retrying with OpenRouter...")
            try:
                from openai import OpenAI
                fallback_client = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=or_key,
                )
                response = fallback_client.chat.completions.create(
                    model       = "google/gemini-2.0-flash-001",
                    messages    = [
                        {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
                        {"role": "user",   "content": query},
                    ],
                    temperature = 0.1,
                    max_tokens  = 1024,
                )
                raw = response.choices[0].message.content.strip()
                raw = re.sub(r'^```(?:json)?\s*\n?', '', raw)
                raw = re.sub(r'\n?\s*```$', '', raw)
                json_match = re.search(r'\{.*\}', raw, re.DOTALL)
                if json_match:
                    raw = json_match.group(0)
                data = json.loads(raw)
                steps = []
                for s in data.get("steps", []):
                    steps.append(PlanStep(
                        step_number=s.get("step_number", len(steps) + 1),
                        action=s.get("action", "ANSWER"),
                        target=str(s.get("target", "")),
                        context=s.get("context") or None,
                        description=s.get("description", ""),
                    ))
                if steps:
                    return MultiStepPlan(
                        original_query=query, intent=data.get("intent", "custom"), steps=steps
                    )
            except Exception as e2:
                print(f"[Planner] OpenRouter fallback also failed: {e2}")
                if groq_key:
                    print("[Planner] Retrying with Groq...")
                    try:
                        from groq import Groq
                        fallback_client = Groq(api_key=groq_key)
                        response = fallback_client.chat.completions.create(
                            model       = "llama-3.3-70b-versatile",
                            messages    = [
                                {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
                                {"role": "user",   "content": query},
                            ],
                            temperature = 0.1,
                            max_tokens  = 1024,
                        )
                        raw = response.choices[0].message.content.strip()
                        raw = re.sub(r'^```(?:json)?\s*\n?', '', raw)
                        raw = re.sub(r'\n?\s*```$', '', raw)
                        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
                        if json_match:
                            raw = json_match.group(0)
                        data = json.loads(raw)
                        steps = []
                        for s in data.get("steps", []):
                            steps.append(PlanStep(
                                step_number=s.get("step_number", len(steps) + 1),
                                action=s.get("action", "ANSWER"),
                                target=str(s.get("target", "")),
                                context=s.get("context") or None,
                                description=s.get("description", ""),
                            ))
                        if steps:
                            return MultiStepPlan(
                                original_query=query, intent=data.get("intent", "custom"), steps=steps
                            )
                    except Exception as e3:
                        print(f"[Planner] Groq fallback also failed: {e3}")

    return None


# ─────────────────────────────────────────────────────────────────────────────
# DETECTION — is this query multi-step?
# ─────────────────────────────────────────────────────────────────────────────

# Keywords that signal multiple actions chained together
MULTISTEP_SIGNALS = [
    r'\band\s+(send|open|type|click|save|write|move|copy|search|fetch|get)\b',
    r'\bthen\s+(send|open|type|click|save|write|move|search)\b',
    r'\bafter\s+(opening|launching|starting)\b',
    r'send\s+.+\s+(message|mail|email)\s+to\b',
    r'(fetch|get|extract|retrieve)\s+.+\s+(save|store|write|put)\s+',
    r'(stock|price|data)\s+.+\s+(excel|spreadsheet|xlsx)',
    r'whatsapp\s+.+\s+to\b',
    r'open\s+\w+\s+and\b',
]

def is_multistep_query(query: str) -> bool:
    """Returns True if the query requires multiple sequential actions."""
    q = query.lower()
    for pattern in MULTISTEP_SIGNALS:
        if re.search(pattern, q):
            return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def plan_multistep(query: str) -> Optional[MultiStepPlan]:
    """
    Main entry point.
    
    1. Try fast pattern matching (no LLM, instant)
    2. Fall back to LLM decomposition
    
    Returns MultiStepPlan or None if it's a single-step query.
    """
    if not is_multistep_query(query):
        return None

    # Fast path: known patterns
    plan = _try_pattern_match(query)
    if plan:
        print(f"[Planner] Pattern match → intent='{plan.intent}', {len(plan.steps)} steps")
        return plan

    # LLM path: complex/custom queries
    plan = _plan_with_llm(query)
    if plan:
        print(f"[Planner] LLM plan → intent='{plan.intent}', {len(plan.steps)} steps")
        return plan

    return None
