"""
handlers.py
===========
Routes agent actions to the correct capability handler.
Returns structured result with metadata for the frontend.
"""

import os
import re
import time
import asyncio
import mimetypes
import urllib.parse
from datetime import datetime
from typing import List, Optional, Dict, Any

# Import capabilities
from capabilities.browser_agent         import browser_agent
from capabilities.excel_manipulation    import (
    read_sheet_data, write_cell, append_row,
    delete_row, set_style, convert_xls_to_xlsx,
    enable_pivot_table_refresh
)
from capabilities.report_generator      import generate_report_from_data
from capabilities.code_generator        import generate_and_run_script
from execution.system_utils             import execute_generative_command

# ─────────────────────────────────────────────────────
# SITE MAP
# ─────────────────────────────────────────────────────

SITE_MAP: Dict[str, str] = {
    "amazon":    "https://www.amazon.in",
    "google":    "https://www.google.com",
    "gmail":     "https://mail.google.com",
    "youtube":   "https://www.youtube.com",
    "github":    "https://github.com",
    "facebook":  "https://www.facebook.com",
    "twitter":   "https://twitter.com",
    "linkedin":  "https://www.linkedin.com",
    "flipkart":  "https://www.flipkart.com",
    "wikipedia": "https://www.wikipedia.org",
    "myntra":    "https://www.myntra.com",
    "meesho":    "https://www.meesho.com",
    "ajio":      "https://www.ajio.com",
    "swiggy":    "https://www.swiggy.com",
    "zomato":    "https://www.zomato.com",
    "paytm":     "https://www.paytm.com",
    "imdb":      "https://www.imdb.com",
    "snapdeal":  "https://www.snapdeal.com",
    "irctc":     "https://www.irctc.co.in",
    "weather":   "https://weather.com",
    "netflix":   "https://www.netflix.com",
    "spotify":   "https://www.spotify.com",
    "reddit":    "https://www.reddit.com",
    "discord":   "https://discord.com",
}


# ─────────────────────────────────────────────────────
# MAIN ACTION ROUTER
# ─────────────────────────────────────────────────────

async def handle_action(
    action:     str,
    target:     str,
    context:    Optional[str],
    user_input: str,
    task_id:    str = "default",
    reasoning:  Optional[str] = None
) -> Dict[str, Any]:
    """
    Routes actions to the correct capability handler.
    Returns structured result with metadata for the frontend.
    """
    trace_logs = []
    if reasoning:
        trace_logs.append(f"AI Reasoning: {reasoning}")

    result     = ""
    tool_used  = "None"
    attachment = None
    action     = action.upper()

    try:

        # ── EXCEL ──────────────────────────────────────────

        if action == "EXCEL_READ":
            tool_used = "Excel (Read)"
            target    = _resolve_excel_path(target)
            result    = read_sheet_data(target, sheet_name=context)

        elif action == "EXCEL_WRITE":
            tool_used = "Excel (Write Cell)"
            target    = _resolve_excel_path(target)
            if context:
                parts = [p.strip() for p in context.split(",")]
                if len(parts) >= 3:
                    sheet, cell, val = parts[0], parts[1], ",".join(parts[2:])
                elif len(parts) == 2:
                    sheet, cell, val = None, parts[0], parts[1]
                else:
                    sheet, cell, val = None, "A1", context
                before_view = read_sheet_data(target, sheet_name=sheet, fmt="html")
                res_msg     = write_cell(target, sheet, cell, val)
                after_view  = read_sheet_data(target, sheet_name=sheet, fmt="html")
                result      = _format_excel_result(before_view, after_view, res_msg)
            else:
                result = "❌ Error: Context missing for Write."

        elif action == "EXCEL_ADD_ROW":
            tool_used = "Excel (Append Row)"
            target    = _resolve_excel_path(target)
            if context:
                data        = _parse_row_data(context)
                before_view = read_sheet_data(target, fmt="html")
                res_msg     = append_row(target, None, data)
                after_view  = read_sheet_data(target, fmt="html")
                result      = _format_excel_result(before_view, after_view, res_msg)
            else:
                result = "❌ Error: Context missing for Append Row."

        elif action == "EXCEL_DELETE_ROW":
            tool_used = "Excel (Delete Row)"
            target    = _resolve_excel_path(target)
            idx       = _resolve_row_index(target, context, trace_logs)
            if idx > 0:
                before_view = read_sheet_data(target, fmt="html")
                res_msg     = delete_row(target, None, idx)
                after_view  = read_sheet_data(target, fmt="html")
                result      = _format_excel_result(before_view, after_view, res_msg)
            else:
                result = "❌ Error: Invalid row index."

        elif action == "EXCEL_STYLE":
            tool_used = "Excel (Style)"
            target    = _resolve_excel_path(target)
            if context:
                context_clean = re.sub(r"[\(\)]", "", context).strip()
                parts = [p.strip() for p in context_clean.split(",")]
                cell  = parts[0]
                color = parts[1] if len(parts) >= 2 else parts[0]

                if len(parts) == 1:
                    cell  = cell if any(
                        kw in cell.lower()
                        for kw in ["header", "column", "row", "A", "B", ":"]
                    ) else "headers"
                    color = parts[0]

                color = color.lower().replace("color", "").replace("in ", "").strip()
                cell  = cell.lower().replace("in ", "").strip()

                before_view = read_sheet_data(target, fmt="html")
                res_msg     = set_style(
                    target, None, cell,
                    bg_color   = color,
                    font_color = color,
                    bold       = "bold"   in context.lower(),
                    border     = "border" in context.lower()
                )
                after_view = read_sheet_data(target, fmt="html")
                result     = _format_excel_result(before_view, after_view, res_msg)
            else:
                result = "❌ Error: Context requires styling details (e.g., 'headers, red')."

        elif action == "EXCEL_REFRESH_PIVOTS":
            tool_used = "Excel (Refresh Pivots)"
            target    = _resolve_excel_path(target)
            result    = enable_pivot_table_refresh(target)

        # ── DOCUMENT / CODE ────────────────────────────────

        elif action == "DOC_REPORT":
            tool_used   = "Document Intelligence (Report)"
            target_file = _resolve_file_robust(target)
            trace_logs.append(f"Generating report for: {context or user_input}")
            before_view   = read_sheet_data(target_file, fmt="html") if os.path.exists(target_file) else ""
            report_result = generate_report_from_data(
                task      = context or user_input,
                file_path = target_file
            )
            if report_result["status"] == "success":
                output_path = report_result["output_path"]
                summary     = report_result["summary"]
                result = (
                    f"<div class='excel-comparison'>"
                    f"<div><h4>Source Data</h4>{before_view}</div></div>"
                    f"<p><strong>✅ {summary}</strong></p>"
                    f"<p>📄 Saved to: <code>{output_path}</code></p>"
                )
                if output_path and os.path.exists(output_path):
                    attachment = {
                        "type": "file",
                        "url":  f"http://localhost:8000/files/stream?path={urllib.parse.quote(output_path)}",
                        "name": os.path.basename(output_path)
                    }
            else:
                result = f"❌ Report generation failed: {report_result.get('error', 'Unknown error')}"

        elif action == "DYNAMIC_CODE":
            task_desc   = context or "Perform the requested operation"
            target_file = _resolve_dynamic_file(target, task_desc)

            task_lower    = task_desc.lower()
            data_keywords = [
                "stock", "closing", "opening", "price", "retrieve", "fetch",
                "nikkei", "sensex", "nifty", "s&p", "dow", "nasdaq",
                "exchange rate", "currency", "gold", "silver", "crypto",
                "bitcoin", "market", "share price"
            ]
            is_data_task = any(kw in task_lower for kw in data_keywords)

            if is_data_task:
                tool_used = "Data Retriever"
                trace_logs.append(f"Retrieving data: {task_desc}")
                from capabilities.data_retriever import retrieve_data_and_create_excel
                result = retrieve_data_and_create_excel(task=task_desc, file_path=target_file)
            else:
                tool_used = "Dynamic AI Coder"
                trace_logs.append(f"Generating script for: {task_desc} on {target_file}")
                is_excel    = target_file.lower().endswith((".xls", ".xlsx", ".csv"))
                before_view = read_sheet_data(target_file, fmt="html") if is_excel and os.path.exists(target_file) else ""
                script_result = generate_and_run_script(task=task_desc, file_path=target_file)
                if is_excel and os.path.exists(target_file):
                    after_view = read_sheet_data(target_file, fmt="html")
                    result     = _format_excel_result(before_view, after_view, script_result)
                else:
                    result = script_result

        # ── BROWSER ────────────────────────────────────────

        elif action == "WEB_CONTROL":
            tool_used = "AI Browser Agent"
            from capabilities.security_manager import security_manager

            clean_target  = security_manager.sanitize_input(target)
            clean_context = security_manager.sanitize_input(context) if context else ""
            goal          = f"{clean_target} {clean_context}".strip()
            url           = _resolve_url(clean_target, clean_context)

            trace_logs.append(f"Browser Agent: navigating to {url}, goal: {goal}")

            try:
                from execution.agentic_orchestrator import orchestrator
                from execution.task_memory          import get_task_memory

                memory      = get_task_memory(task_id, create=True)
                task_result = await orchestrator.execute_task(
                    goal        = goal,
                    starting_url = url,
                    task_id     = task_id
                )

                result = task_result.summary
                trace_logs.extend(task_result.logs)

                if task_result.extracted:
                    result += "\n\n**Extracted Data:**\n"
                    for k, v in task_result.extracted.items():
                        result += f"- {k}: {v}\n"

                if task_result.attachment:
                    attachment = task_result.attachment

                if not task_result.success and task_result.error:
                    result += f"\n\n⚠️ Errors occurred:\n{task_result.error}"

            except Exception as e:
                import traceback
                result = f"❌ Browser Agent crashed: {e}\n{traceback.format_exc()}"

        # ── DIRECT ANSWER ───────────────────────────────────

        elif action == "ANSWER":
            tool_used = "AI Direct Answer"

            if context and context.startswith("FINAL_ANSWER:"):
                answer = context.replace("FINAL_ANSWER:", "", 1)
                trace_logs.append("Using pre-generated answer (latency optimized)")
            else:
                from execution.nlu import generate_text_content
                prompt = target if target and len(target) > 5 else (context or user_input)
                trace_logs.append(f"Generating answer for: {prompt}")
                # ✅ Fix: run sync function in thread to avoid blocking event loop
                answer = await asyncio.to_thread(generate_text_content, prompt)

            result     = answer
            attachment = {
                "type":    "text_card",
                "title":   f"AI Answer: {target[:30]}...",
                "content": answer
            }

        # ── DESKTOP FILE / APP OPERATIONS ───────────────────

        elif action == "OPEN":
            tool_used = "OS Shell"
            from capabilities.desktop_ops        import open_application, _is_visual_rpa, _get_rpa_target
            from capabilities.desktop_automation import desktop_agent

            resolved = _resolve_file_robust(target)
            trace_logs.append(f"Opening: {resolved}")

            # ✅ Fix: Handle VISUAL_RPA token properly
            if _is_visual_rpa(resolved):
                result = desktop_agent.search_start_menu(_get_rpa_target(resolved))
            else:
                result = open_application(resolved if os.path.exists(resolved) else target)

            # Remember last opened app for visual actions
            try:
                desktop_agent.last_window_title = target
            except Exception:
                pass

            await asyncio.sleep(2)

        elif action == "CLOSE":
            tool_used = "OS Shell"
            from capabilities.desktop_ops import close_application
            trace_logs.append(f"Closing: {target}")
            result = close_application(target)

        elif action == "DELETE":
            tool_used = "OS Shell"
            from capabilities.desktop_ops import delete_file, _is_visual_rpa
            resolved = _resolve_file_robust(target)
            trace_logs.append(f"Deleting: {resolved}")

            if _is_visual_rpa(resolved):
                result = f"❌ Cannot delete '{target}' — file not found on disk."
            else:
                result = delete_file(resolved)

        elif action == "RENAME":
            tool_used = "OS Shell"
            from capabilities.desktop_ops import rename_file, _is_visual_rpa
            resolved = _resolve_file_robust(target)
            trace_logs.append(f"Renaming '{resolved}' → '{context}'")

            # ✅ Fix: Guard against VISUAL_RPA token
            if _is_visual_rpa(resolved):
                result = f"❌ Cannot rename '{target}' — file not found on disk."
            elif not context:
                result = "❌ Error: New name not provided for rename."
            else:
                result = rename_file(resolved, context)

        elif action == "MOVE":
            tool_used = "OS Shell"
            from capabilities.desktop_ops import move_file, _is_visual_rpa
            resolved = _resolve_file_robust(target)
            dest     = context or ""
            trace_logs.append(f"Moving '{resolved}' → '{dest}'")

            # ✅ Fix: Guard against VISUAL_RPA token
            if _is_visual_rpa(resolved):
                result = f"❌ Cannot move '{target}' — file not found on disk."
            elif not dest:
                result = "❌ Error: Destination not provided for move."
            else:
                result = move_file(resolved, dest)

        elif action == "COPY":
            tool_used = "OS Shell"
            from capabilities.desktop_ops import copy_file, _is_visual_rpa
            resolved = _resolve_file_robust(target)
            dest     = context or ""
            trace_logs.append(f"Copying '{resolved}' → '{dest}'")

            if _is_visual_rpa(resolved):
                result = f"❌ Cannot copy '{target}' — file not found on disk."
            elif not dest:
                result = "❌ Error: Destination not provided for copy."
            else:
                result = copy_file(resolved, dest)

        elif action == "LIST_FILES":
            tool_used = "OS Shell"
            from capabilities.desktop_ops import list_files
            trace_logs.append(f"Listing files in: {target}")
            result = list_files(target, extension=context or "")

        # ── VISUAL RPA ──────────────────────────────────────

        elif action == "CLICK_TEXT":
            tool_used = "Visual RPA (Click)"
            from capabilities.desktop_automation import desktop_agent
            trace_logs.append(f"Clicking text: '{target}' (Window: {context})")
            result = desktop_agent.click_text(target, window_title=context)

        elif action == "TYPE_DESKTOP":
            tool_used = "Visual RPA (Type)"
            from capabilities.desktop_automation import desktop_agent
            print(f"[Handler] TYPE_DESKTOP called with target='{target}', window='{context}'")
            trace_logs.append(f"Typing: '{target}' (Window: {context})")
            result = desktop_agent.type_text(target, window_title=context)

        elif action == "READ_SCREEN":
            tool_used = "Visual RPA (OCR)"
            from capabilities.vision_engine import vision_engine
            trace_logs.append("Reading screen content via OCR...")
            result = vision_engine.read_screen_text()

        elif action == "SCREENSHOT":
            tool_used = "Visual RPA (Screenshot)"
            from capabilities.desktop_automation import desktop_agent
            trace_logs.append("Capturing screenshot...")
            b64 = desktop_agent.capture_screenshot()
            result     = "✅ Screenshot captured"
            # Standardize for TimelineFeed WebResultViewer
            attachment = {
                "type": "web_result", 
                "screenshot": f"data:image/png;base64,{b64}" if not b64.startswith("data:") else b64,
                "data": "Screenshot of the current desktop state."
            }

        elif action == "SEARCH_START_MENU":
            tool_used = "Visual RPA (Start Menu)"
            from capabilities.desktop_automation import desktop_agent
            trace_logs.append(f"Searching Start Menu for: '{target}'")
            result = await desktop_agent.search_start_menu_async(target, action="open")

        elif action == "PRESS_KEY":
            tool_used = "Visual RPA (Keyboard)"
            from capabilities.desktop_automation import desktop_agent
            trace_logs.append(f"Pressing key: {target}")
            result = desktop_agent.press_key(target)

        elif action == "SCROLL":
            tool_used = "Visual RPA (Mouse)"
            from capabilities.desktop_automation import desktop_agent
            trace_logs.append(f"Scrolling: {target} clicks")
            try:
                clicks = int(target) if target.isdigit() else 3
                result = desktop_agent.scroll(clicks)
            except:
                result = desktop_agent.scroll(3)

        elif action == "SEARCH":
            tool_used = "Universal Resolver"
            from capabilities.desktop_ops import resolve_target_path, _is_visual_rpa
            trace_logs.append(f"Searching for: {target}")
            path = resolve_target_path(target)
            if not path:
                result = f"❌ Could not find '{target}'"
            elif _is_visual_rpa(path):
                result = f"⚠️ '{target}' not found on disk — try: open {target}"
            else:
                result = f"✅ Found: {path}"

        # ── MULTI-STEP ORCHESTRATOR ─────────────────────────

        elif action == "MULTI_STEP_COMPLETE":
            tool_used = "Task Orchestrator"
            summary   = context or "Multi-step task completed."
            steps     = target
            trace_logs.append(f"Orchestrator finished {steps} steps.")
            
            # Format a nice summary
            result = (
                f"✅ **Multi-Step Task Completed**\n\n"
                f"{summary}\n"
                f"_(Executed {steps} steps sequentially)_"
            )

        elif action == "MULTI_STEP_FAILED":
            tool_used = "Task Orchestrator"
            error_msg = target or "Unknown error"
            trace_logs.append(f"Orchestrator failed: {error_msg}")
            result = f"❌ **Multi-Step Task Failed**\n\nError: {error_msg}"

        # ── UNKNOWN ─────────────────────────────────────────

        else:
            result = f"⚠️ Action '{action}' is not implemented yet."

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        trace_logs.append(f"CRITICAL ERROR in handle_action: {error_trace}")
        result = f"❌ Error executing {action}: {str(e)}\n\nTraceback:\n{error_trace}"

    return {
        "result":     result,
        "tool_used":  tool_used,
        "trace_logs": trace_logs,
        "attachment": attachment
    }


# ─────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────

def _resolve_excel_path(target: str) -> str:
    """Resolve and normalize an Excel file path."""
    from utils.resolver import resolve_file_arg

    # Strip common prefix words
    target = re.sub(
        r"^(open|launch|get|show|view|find|the|a|an)\s+",
        "", str(target), flags=re.IGNORECASE
    ).strip()

    full_path = resolve_file_arg(target)

    # Auto-convert .xls → .xlsx
    if full_path.lower().endswith(".xls"):
        converted = convert_xls_to_xlsx(full_path)
        if converted:
            return converted

    return full_path


def _format_excel_result(before: str, after: str, action_msg: str) -> str:
    """Format before/after Excel views into an HTML comparison card."""
    return (
        f"<div class='excel-comparison'>"
        f"<div><h4>Before Update</h4>{before}</div>"
        f"<div><h4>After Update</h4>{after}</div>"
        f"</div>"
        f"<p><strong>Action:</strong> {action_msg}</p>"
    )


def _parse_row_data(context: str) -> Any:
    """Parse row data from context string into dict or list."""
    if any(sep in context for sep in ["=", " is ", ":"]):
        try:
            data_dict = {}
            for arg in re.split(r",|\s+and\s+", context):
                arg = arg.strip()
                if not arg:
                    continue
                if "=" in arg:
                    k, v = arg.split("=", 1)
                elif " is " in arg:
                    k, v = arg.split(" is ", 1)
                elif ":" in arg:
                    k, v = arg.split(":", 1)
                else:
                    continue
                data_dict[k.strip()] = v.strip()
            return data_dict if data_dict else [d.strip() for d in context.split(",")]
        except Exception:
            pass
    return [d.strip() for d in context.split(",")]


def _resolve_row_index(target: str, context: str, logs: list) -> int:
    """Resolve 'last', a number, or a string to a row index."""
    try:
        c_low = context.strip().lower() if context else ""
        if "last" in c_low:
            import openpyxl
            wb  = openpyxl.load_workbook(target)
            idx = wb.active.max_row
            logs.append(f"Resolved 'last row' to index {idx}")
            return idx
        digits = "".join(filter(str.isdigit, context or ""))
        return int(digits) if digits else 0
    except Exception:
        return 0


def _resolve_file_robust(target: str) -> str:
    """
    Resolve a human-friendly file/app name to an absolute path.
    Uses the hardened 5-stage resolver from desktop_ops.
    """
    from capabilities.desktop_ops import resolve_target_path

    # Strip common prefix words
    cleaned = re.sub(
        r"^(open|launch|get|show|view|find|the|a|an)\s+",
        "", str(target), flags=re.IGNORECASE
    ).strip()

    if not cleaned:
        return str(target)

    path = resolve_target_path(cleaned)
    return path if path else cleaned


def _resolve_dynamic_file(target: str, task_desc: str) -> str:
    """Resolve dynamic file references for code generation tasks."""
    if target == "active_workbook" or (
        not os.path.exists(target) and "." not in target
    ):
        potential = [
            w.strip("',\"") for w in task_desc.split()
            if w.lower().endswith((".xlsx", ".xls", ".csv"))
        ]
        if potential:
            return potential[-1]

        quoted = re.search(
            r'["\']([^"\']+\.(xlsx|xls|csv))["\']',
            task_desc, re.IGNORECASE
        )
        if quoted:
            return quoted.group(1)

    return _resolve_file_robust(target)


def _resolve_url(target: str, context: str = "") -> str:
    """Resolve a target string to a full URL."""
    url_match = re.search(r"(https?://[^\s]+)", target)
    if url_match:
        return url_match.group(1)

    if target.startswith("www."):
        return "https://" + target

    combined = f"{target} {context}".lower()
    for name, url in SITE_MAP.items():
        if name in combined:
            return url

    if re.search(r"\w+\.\w+", target):
        return f"https://{target}" if not target.startswith("http") else target

    search_term = target.replace("https://", "").replace("http://", "")
    return f"https://www.google.com/search?q={urllib.parse.quote(search_term)}"
