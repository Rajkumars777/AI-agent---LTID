import os
import re
import time
import asyncio
import mimetypes
import urllib.parse
from datetime import datetime
from typing import List, Optional, Dict, Any

# Import capabilities
from capabilities.browser_agent import browser_agent
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
        if action == "EXCEL_READ":
            tool_used = "Excel (Read)"
            target = _resolve_excel_path(target)
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
            task_desc = context if context else "Perform the requested operation"
            target_file = _resolve_dynamic_file(target, task_desc)
            
            # Check if this is a data retrieval task (stock, prices, exchange rates, etc.)
            task_lower = task_desc.lower()
            data_keywords = ["stock", "closing", "opening", "price", "retrieve", "fetch",
                             "nikkei", "sensex", "nifty", "s&p", "dow", "nasdaq",
                             "exchange rate", "currency", "gold", "silver", "crypto",
                             "bitcoin", "market", "share price"]
            is_data_task = any(kw in task_lower for kw in data_keywords)
            
            if is_data_task:
                tool_used = "Data Retriever"
                trace_logs.append(f"Retrieving data: {task_desc}")
                from capabilities.data_retriever import retrieve_data_and_create_excel
                result = retrieve_data_and_create_excel(task=task_desc, file_path=target_file)
            else:
                tool_used = "Dynamic AI Coder"
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
                    "irctc": "https://www.irctc.co.in",
                    "weather": "https://weather.com",
                    "example": "https://www.example.com",
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

            # 3. Run in thread (sync Playwright cannot run on async loop)
            try:
                result = await asyncio.to_thread(
                    browser_agent.run_task, url, goal
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

        elif action == "OPEN":
            tool_used = "OS Shell"
            from capabilities.desktop_ops import open_application
            # Try to resolve file path first, if not found, treat as app name
            resolved = _resolve_file_robust(target)
            final_target = resolved if os.path.exists(resolved) else target
            
            trace_logs.append(f"Opening: {final_target}")
            result = open_application(final_target)
            
        elif action == "CLOSE":
            tool_used = "OS Shell"
            from capabilities.desktop_ops import close_application
            trace_logs.append(f"Closing: {target}")
            result = close_application(target)
            
        elif action == "DELETE":
            tool_used = "OS Shell"
            from capabilities.desktop_ops import delete_file
            resolved = _resolve_file_robust(target)
            trace_logs.append(f"Deleting: {resolved}")
            result = delete_file(resolved)

        elif action == "RENAME":
            tool_used = "OS Shell"
            from capabilities.desktop_ops import rename_file
            resolved = _resolve_file_robust(target)
            trace_logs.append(f"Renaming {resolved} to {context}")
            result = rename_file(resolved, context)

        elif action == "MOVE":
            tool_used = "OS Shell"
            from capabilities.desktop_ops import move_file
            resolved = _resolve_file_robust(target)
            dest = _resolve_file_robust(context) if context else ""
            trace_logs.append(f"Moving {resolved} to {dest}")
            result = move_file(resolved, dest)

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
    from utils.resolver import resolve_file_arg
    # CLEANUP: Strip common prefix words
    target = re.sub(r'^(open|launch|get|show|view|find|the|a|an)\s+', '', str(target), flags=re.IGNORECASE).strip()
    
    full_path = resolve_file_arg(target)
    if full_path.lower().endswith(".xls"):
         new_target = convert_xls_to_xlsx(full_path)
         if new_target: return new_target
    return full_path

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
    from utils.resolver import resolve_file_arg
    # CLEANUP: Strip "open ", "the ", etc. in case NLU leaked it
    target = re.sub(r'^(open|launch|get|show|view|find|the|a|an)\s+', '', str(target), flags=re.IGNORECASE).strip()
    return resolve_file_arg(target)

def _resolve_dynamic_file(target: str, task_desc: str) -> str:
    if target == "active_workbook" or (not os.path.exists(target) and "." not in target):
         potential = [w.strip("',\"") for w in task_desc.split() if w.lower().endswith(('.xlsx', '.xls', '.csv'))]
         if potential: return potential[-1]
         quoted = re.search(r'["\']([^"\']+\.(xlsx|xls|csv))["\']', task_desc, re.IGNORECASE)
         if quoted: return quoted.group(1)
    return _resolve_file_robust(target)
