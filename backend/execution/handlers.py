import os
import re
import time
import asyncio
import mimetypes
import urllib.parse
from datetime import datetime
from typing import List, Optional, Dict, Any

# Import capabilities
from capabilities.desktop import (
    launch_application, type_text, find_and_open_file, 
    close_application, rename_file, move_file, 
    find_file_paths, send_key, delete_file
)
from capabilities.excel_manipulation import (
    read_sheet_data, write_cell, append_row, 
    delete_row, set_style, convert_xls_to_xlsx,
    enable_pivot_table_refresh
)

from capabilities.report_generator import generate_report_from_data
from capabilities.code_generator import generate_and_run_script
from execution.system_utils import execute_generative_command

async def handle_action(action: str, target: str, context: Optional[str], user_input: str, task_id: str = "default", reasoning: Optional[str] = None) -> Dict[str, Any]:
    """
    Routes actions to the appropriate capability handler and returns the result with metadata.
    """
    trace_logs = []
    if reasoning:
        trace_logs.append(f"AI Reasoning: {reasoning}")
    result = ""
    tool_used = "None"
    attachment = None
    action = action.upper()

    from execution.interaction import ask_user

    try:
        if action in ["OPEN", "LAUNCH", "PLAY", "VIEW", "SHOW", "GET", "SEARCH"]:
            tool_used = "Desktop Automation (Open)"
            # FALLBACK SANITIZATION: Strip "open ", "launch " etc from target if NLU leaked it
            target = re.sub(r'^(open|launch|get|show|view|find|the|a|an)\s+', '', target, flags=re.IGNORECASE).strip()
            launch_res = launch_application(target)
            file_path = None
            
            if "Could not find" in launch_res or "not in the system" in launch_res:
                trace_logs.append(f"App launch failed. Searching for file '{target}'...")
                file_path = find_and_open_file(target)
                
                if isinstance(file_path, dict) and file_path.get("status") == "multiple_files":
                    # PAUSE AND ASK USER
                    files = file_path.get("files", [])
                    question = f"I found multiple files matching '{target}'. Which one should I open?"
                    options = [{"label": f"Open {os.path.basename(f)}", "value": f"open {f}"} for f in files]
                    
                    user_selection = await ask_user(task_id, question, {"options": options})
                    
                    if isinstance(user_selection, str) and "open " in user_selection:
                         target_file = user_selection.replace("open ", "")
                         result = launch_application(target_file)
                         file_path = target_file
                    else:
                         result = f"I found multiple files: {', '.join([os.path.basename(f) for f in files])}"
                         attachment = {"type": "options", "data": options}
                else:
                    result = str(file_path)
            else:
                result = launch_res

            # Media Handling
            if file_path and "not found" not in str(file_path).lower() and "Found multiple" not in str(file_path) and os.path.exists(str(file_path)):
                mime, _ = mimetypes.guess_type(str(file_path))
                if mime:
                    media_type = None
                    if mime.startswith("image/"): media_type = "image"
                    elif mime.startswith("video/"): media_type = "video"
                    elif mime.startswith("audio/"): media_type = "audio"
                    
                    if media_type:
                        encoded_path = urllib.parse.quote(str(file_path))
                        attachment = {
                            "type": media_type,
                            "url": f"http://localhost:8000/files/stream?path={encoded_path}",
                            "name": os.path.basename(str(file_path))
                        }
                        result = f"Opened/Playing {os.path.basename(str(file_path))}"
            
            if "Launched" in result or "Opened" in result:
                 trace_logs.append("Waiting 3s for app to focus...")
                 time.sleep(3) 
                 if any(kw in target.lower() for kw in ["word", "excel", "powerpoint"]):
                     trace_logs.append("Sending ENTER to create New Document...")
                     send_key("enter")
                     time.sleep(1)

        elif action in ["CLOSE", "STOP", "EXIT", "KILL"]:
            tool_used = "Desktop Automation (Close)"
            result = close_application(target)

        elif action in ["TYPE", "WRITE"]:
            tool_used = "Desktop Automation (Type)"
            is_async = context and context.startswith("GENERATE_ASYNC")
            app_name = context.split(":", 1)[1] if is_async and ":" in context else "Notepad"
            
            if is_async or context == "GENERATE":
                 trace_logs.append(f"Triggering Parallel Execution for '{app_name}'...")
                 result = await execute_generative_command(app_name, target)
            else:
                 result = type_text(target)

        elif action == "RENAME":
            tool_used = "Desktop Automation (Rename)"
            result = rename_file(target, context) if context else "Error: New name not provided."

        elif action == "MOVE":
            tool_used = "Desktop Automation (Move)"
            result = move_file(target, context) if context else "Error: Destination not provided."

        elif action in ["DELETE", "REMOVE"]:
            tool_used = "Desktop Automation (Delete)"
            result = delete_file(target)

        elif action == "EXCEL_READ":
            tool_used = "Excel (Read)"
            if not os.path.exists(target) and not os.path.isabs(target):
                 found = find_file_paths(target)
                 if found: target = found[0]
            result = read_sheet_data(target, sheet_name=context)

        elif action == "EXCEL_WRITE":
            tool_used = "Excel (Write Cell)"
            target = _resolve_excel_path(target)
            if context:
                parts = [p.strip() for p in context.split(',')]
                sheet, cell, val = (parts[0], parts[1], ",".join(parts[2:])) if len(parts) >= 3 else (None, parts[0], parts[1]) if len(parts) == 2 else (None, "A1", context)
                before_view = read_sheet_data(target, sheet_name=sheet, fmt="html")
                res_msg = write_cell(target, sheet, cell, val)
                after_view = read_sheet_data(target, sheet_name=sheet, fmt="html")
                result = _format_excel_result(before_view, after_view, res_msg)
            else:
                result = "Error: Context missing for Write."

        elif action == "EXCEL_ADD_ROW":
            tool_used = "Excel (Append Row)"
            target = _resolve_excel_path(target)
            if context:
                data = _parse_row_data(context)
                before_view = read_sheet_data(target, fmt="html")
                res_msg = append_row(target, None, data)
                after_view = read_sheet_data(target, fmt="html")
                result = _format_excel_result(before_view, after_view, res_msg)
            else:
                result = "Error: Context missing for Append Row."

        elif action == "EXCEL_DELETE_ROW":
            tool_used = "Excel (Delete Row)"
            target = _resolve_excel_path(target)
            idx = _resolve_row_index(target, context, trace_logs)
            if idx > 0:
                before_view = read_sheet_data(target, fmt="html")
                res_msg = delete_row(target, None, idx)
                after_view = read_sheet_data(target, fmt="html")
                result = _format_excel_result(before_view, after_view, res_msg)
            else:
                result = "Error: Invalid row index."

        elif action == "EXCEL_STYLE":
            tool_used = "Excel (Style)"
            target = _resolve_excel_path(target)
            if context:
                # Cleanup context (strip parens, extra spaces)
                context_clean = re.sub(r'[\(\)]', '', context).strip()
                # Context can be "Cell/Range, Color" 
                parts = [p.strip() for p in context_clean.split(',')]
                cell = parts[0]
                color = parts[1] if len(parts) >= 2 else parts[0]
                
                # If only one part was provided, assume it's the color and target is the range
                if len(parts) == 1:
                    cell = cell if any(kw in cell.lower() for kw in ["header", "column", "row", "A", "B", ":"]) else "headers"
                    color = parts[0]

                # Cleanup color string (e.g. "red color" -> "red")
                color = color.lower().replace("color", "").replace("in ", "").strip()
                cell = cell.lower().replace("in ", "").strip()
                
                before_view = read_sheet_data(target, fmt="html")
                # Apply as both bg and font if ambiguous, or just font if specified
                res_msg = set_style(target, None, cell, bg_color=color, font_color=color, bold="bold" in context.lower(), border="border" in context.lower())
                after_view = read_sheet_data(target, fmt="html")
                result = _format_excel_result(before_view, after_view, res_msg)
            else:
                result = "Error: Context requires styling details (e.g., 'headers, red')."

        elif action == "EXCEL_REFRESH_PIVOTS":
            tool_used = "Excel (Refresh Pivots)"
            target = _resolve_excel_path(target)
            result = enable_pivot_table_refresh(target)

        elif action == "DOC_REPORT":
            tool_used = "Document Intelligence (Report)"
            target_file = _resolve_file_robust(target)
            trace_logs.append(f"Generating structured report for: {context if context else user_input}")
            before_view = read_sheet_data(target_file, fmt="html") if os.path.exists(target_file) else ""
            report_result = generate_report_from_data(task=context if context else user_input, file_path=target_file)
            
            if report_result["status"] == "success":
                output_path, summary = report_result["output_path"], report_result["summary"]
                result = f"<div class='excel-comparison'><div><h4>Source Data</h4>{before_view}</div></div><p><strong>✅ {summary}</strong></p><p>📄 Saved to: <code>{output_path}</code></p>"
                if output_path and os.path.exists(output_path):
                    attachment = {"type": "file", "url": f"http://localhost:8000/files/stream?path={urllib.parse.quote(output_path)}", "name": os.path.basename(output_path)}
            else:
                result = f"❌ Report generation failed: {report_result.get('error', 'Unknown error')}"

        elif action == "DYNAMIC_CODE":
            tool_used = "Dynamic AI Coder"
            task_desc = context if context else "Perform the requested operation"
            target_file = _resolve_dynamic_file(target, task_desc)
            trace_logs.append(f"Generating custom script for: {task_desc} on {target_file}")
            is_excel = target_file.lower().endswith(('.xls', '.xlsx', '.csv'))
            before_view = read_sheet_data(target_file, fmt="html") if is_excel and os.path.exists(target_file) else ""
            script_result = generate_and_run_script(task=task_desc, file_path=target_file)
            if is_excel and os.path.exists(target_file):
                after_view = read_sheet_data(target_file, fmt="html")
                result = _format_excel_result(before_view, after_view, script_result)
            else:
                result = script_result

        elif action == "WEB_CONTROL":
            tool_used = "AI Browser Agent"
            import json
            import re as _re
            from capabilities.browser_agent import browser_agent
            from capabilities.security_manager import security_manager

            # 1. Sanitize secrets
            clean_target = security_manager.sanitize_input(target)
            clean_context = security_manager.sanitize_input(context) if context else ""
            goal = f"{clean_target} {clean_context}".strip()

            # 2. Resolve URL
            url = None
            # Direct URL
            url_match = _re.search(r'(https?://[^\s]+)', clean_target)
            if url_match:
                url = url_match.group(1)
            elif clean_target.startswith("www."):
                url = "https://" + clean_target
            else:
                # Map common site names to URLs
                site_map = {
                    "amazon": "https://www.amazon.in",
                    "google": "https://www.google.com",
                    "gmail": "https://mail.google.com",
                    "youtube": "https://www.youtube.com",
                    "github": "https://github.com",
                    "facebook": "https://www.facebook.com",
                    "twitter": "https://twitter.com",
                    "linkedin": "https://www.linkedin.com",
                    "flipkart": "https://www.flipkart.com",
                    "wikipedia": "https://www.wikipedia.org",
                    "myntra": "https://www.myntra.com",
                    "meesho": "https://www.meesho.com",
                    "ajio": "https://www.ajio.com",
                    "swiggy": "https://www.swiggy.com",
                    "zomato": "https://www.zomato.com",
                    "paytm": "https://www.paytm.com",
                    "imdb": "https://www.imdb.com",
                    "snapdeal": "https://www.snapdeal.com",
                }
                for name, site_url in site_map.items():
                    if name in clean_target.lower() or name in clean_context.lower():
                        url = site_url
                        break
                # Fallback: if target looks like a domain, construct URL
                if not url and _re.search(r'\w+\.\w+', clean_target):
                    url = f"https://www.{clean_target}" if not clean_target.startswith("http") else clean_target
                # Fallback: search Google
                if not url:
                    search_term = clean_target.replace("https://", "").replace("http://", "")
                    url = f"https://www.google.com/search?q={search_term}"

            trace_logs.append(f"Browser Agent: navigating to {url}, goal: {goal}")

            # 3. LLM function for the agent loop
            import dspy
            def llm_fn(prompt):
                 # Bypass dspy.Predict parsing issues by calling LM directly
                 try:
                     resp = dspy.settings.lm(prompt)[0]
                     print(f"[Handler llm_fn] Response length={len(resp)}, first 200 chars: {repr(resp[:200])}", flush=True)
                     return resp
                 except Exception as e:
                     print(f"[Handler llm_fn] LLM call error: {e}", flush=True)
                     return ""

            # 4. Run in thread (sync Playwright cannot run on async loop)
            try:
                result = await asyncio.to_thread(
                    browser_agent.run_task, url, goal, llm_fn, 12
                )
            except Exception as e:
                import traceback
                result = f"Browser Agent crashed: {e}\n{traceback.format_exc()}"

            trace_logs.append(f"Browser Agent result: {result[:300]}")

        elif action == "ANSWER":
            tool_used = "AI Direct Answer"
            
            # LATENCY OPTIMIZATION: If context contains a pre-generated final answer, use it!
            if context and context.startswith("FINAL_ANSWER:"):
                answer = context.replace("FINAL_ANSWER:", "", 1)
                trace_logs.append("Using pre-generated answer from NLU (Latency Optimized)")
            else:
                from execution.nlu import generate_text_content
                # If context is just parameters, we prefer target for the prompt
                prompt = target if target and len(target) > 5 else (context if context else user_input)
                trace_logs.append(f"Generating direct answer for: {prompt}")
                answer = generate_text_content(prompt)
            
            result = answer
            # Create a nice UI card for the answer
            attachment = {
                "type": "text_card",
                "title": f"AI Answer: {target[:30]}...",
                "content": answer
            }

        else:
            result = f"Action '{action}' not implemented yet."
    
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        trace_logs.append(f"CRITICAL ERROR in handle_action: {error_trace}")
        result = f"Error executing {action}: {str(e)}\n\nTraceback:\n{error_trace}"
        
    return {
        "result": result,
        "tool_used": tool_used,
        "trace_logs": trace_logs,
        "attachment": attachment
    }

# Helper Functions
def _resolve_excel_path(target: str) -> str:
    # CLEANUP: Strip "open ", "the ", etc. in case NLU leaked it
    target = re.sub(r'^(open|launch|get|show|view|find|the|a|an)\s+', '', str(target), flags=re.IGNORECASE).strip()
    
    if not os.path.exists(target) and not os.path.isabs(target):
         found = find_file_paths(target)
         if found: target = found[0]
    if target.lower().endswith(".xls"):
         new_target = convert_xls_to_xlsx(target)
         if new_target: target = new_target
    return target

def _format_excel_result(before, after, action_msg) -> str:
    return f"""<div class="excel-comparison"><div><h4>Before Update</h4>{before}</div><div><h4>After Update</h4>{after}</div></div><p><strong>Action:</strong> {action_msg}</p>"""

def _parse_row_data(context: str) -> Any:
    if any(sep in context for sep in ["=", " is ", ":"]):
        try:
            data_dict = {}
            for arg in re.split(r",|\s+and\s+", context):
                arg = arg.strip()
                if not arg: continue
                if "=" in arg: k, v = arg.split("=", 1)
                elif " is " in arg: k, v = arg.split(" is ", 1)
                elif ":" in arg: k, v = arg.split(":", 1)
                else: continue
                data_dict[k.strip()] = v.strip()
            return data_dict if data_dict else [d.strip() for d in context.split(',')]
        except: pass
    return [d.strip() for d in context.split(',')]

def _resolve_row_index(target: str, context: str, logs: list) -> int:
    try:
        c_low = context.strip().lower() if context else ""
        if "last" in c_low:
             import openpyxl
             wb = openpyxl.load_workbook(target)
             idx = wb.active.max_row
             logs.append(f"Resolved 'last row' to index {idx}")
             return idx
        digits = ''.join(filter(str.isdigit, context or ""))
        return int(digits) if digits else 0
    except: return 0

def _resolve_file_robust(target: str) -> str:
    # CLEANUP: Strip "open ", "the ", etc. in case NLU leaked it
    target = re.sub(r'^(open|launch|get|show|view|find|the|a|an)\s+', '', str(target), flags=re.IGNORECASE).strip()
    if os.path.exists(target): return target
    if not os.path.isabs(target):
        found = find_file_paths(target)
        if found: return found[0]
    return target # Fallback

def _resolve_dynamic_file(target: str, task_desc: str) -> str:
    if target == "active_workbook" or (not os.path.exists(target) and "." not in target):
         potential = [w.strip("',\"") for w in task_desc.split() if w.lower().endswith(('.xlsx', '.xls', '.csv'))]
         if potential: return potential[-1]
         quoted = re.search(r'["\']([^"\']+\.(xlsx|xls|csv))["\']', task_desc, re.IGNORECASE)
         if quoted: return quoted.group(1)
    return _resolve_file_robust(target)
