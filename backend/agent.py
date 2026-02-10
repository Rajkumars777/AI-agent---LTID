import dspy
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, List
import operator
from datetime import datetime

# Import capabilities
from capabilities.desktop import launch_application, type_text, find_and_open_file, close_application, rename_file, move_file, find_file_paths
from capabilities.excel_manipulation import read_sheet_data, write_cell, append_row, delete_row, set_style, convert_xls_to_xlsx

# 2. Define State
class AgentState(TypedDict):
    input: str
    messages: Annotated[List[str], operator.add]
    intermediate_steps: List[str]

import os
from dotenv import load_dotenv
load_dotenv()

# Configure DSPy
openrouter_key = os.getenv("OPENROUTER_API_KEY")

if openrouter_key:
    # Use custom OpenRouter Adapter
    print("Using OpenRouter Adapter...")
    from execution.openrouter_adapter import OpenRouterAdapter
    lm = OpenRouterAdapter(
        model='google/gemini-2.0-flash-001',
        api_key=openrouter_key
    )
    dspy.settings.configure(lm=lm)
else:
    print("WARNING: No API Key found for DSPy. NLU will fail.")

from execution.nlu import extract_commands

def execute_tool(state: AgentState):
    user_input = state.get('input', '')
    steps = []
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 1. Cognitive Parsing vs Fast Path
    commands = []
    
    # FAST PATH: Check for simple single OR multiple commands
    import re
    
    # Initialize commands
    commands = []
    
    # Check for DOC_REPORT commands first (extract + store in word/report)
    doc_keywords = ["word document", "word doc", "docx", "report", "store in word", "save to word", "save in word", "create a report", "generate report", "save as document"]
    file_pattern = r'[\w\-\.]+\.(xlsx|xls|csv)'
    has_file = re.search(file_pattern, user_input, re.IGNORECASE)
    is_doc_report = any(kw in user_input.lower() for kw in doc_keywords)
    
    if is_doc_report and has_file:
        file_match = re.search(r'[\w\-\.]+\.(xlsx|xls|csv)', user_input, re.IGNORECASE)
        file_name = file_match.group(0) if file_match else "active_workbook"
        
        from execution.nlu import Command
        commands = [Command(action="DOC_REPORT", target=file_name, context=user_input)]
    
    # Check if this is a QUERY command (who, what, find, filter, list, etc.)
    # These should go directly to DYNAMIC_CODE if they reference a file
    if not commands:
        query_starters = ["who", "what", "which", "find", "filter", "list", "show me", "get", "how many", "count"]
        is_query = any(user_input.lower().strip().startswith(q) for q in query_starters)
        
        if is_query and has_file:
            file_match = re.search(r'[\w\-\.]+\.(xlsx|xls|csv)', user_input, re.IGNORECASE)
            file_name = file_match.group(0) if file_match else "active_workbook"
            
            from execution.nlu import Command
            commands = [Command(action="DYNAMIC_CODE", target=file_name, context=user_input)]
    
    # Only run fast_path if commands weren't set by query detection
    if not commands:
        # Pattern looks for "verb target", allowing validation
        simple_pattern = r"^\s*(open|launch|play|view|show|get|search|close|stop|exit|kill|type|write|set|delete|remove|rename|move|add|generate|create|insert|read|find|filter|who|what|which|list|count)\s+(.+)$"
        
        # Split by comma or ' and ' (ignoring case) - but NOT if it's part of data description
        if not re.search(r'with\s+.+\s+and\s+', user_input, re.IGNORECASE):
            parts = re.split(r",|\s+and\s+", user_input, flags=re.IGNORECASE)
        else:
            parts = [user_input]
        parts = [p.strip() for p in parts if p.strip()]
    
        fast_path_commands = []
        all_simple = True
        
        for part in parts:
            match = re.match(simple_pattern, part, re.IGNORECASE)
            if match:
                verb = match.group(1).upper()
                target = match.group(2).strip()
                
                # A1 IMPROVEMENT: Remove filler words that confuse file search
                filler_words = ["the ", "my ", "this ", "that ", "a "]
                for filler in filler_words:
                    if target.lower().startswith(filler):
                        target = target[len(filler):]
                        break
                
                # Normalize Verb
                if verb in ["LAUNCH", "PLAY", "VIEW", "SHOW", "GET", "SEARCH"]: verb = "OPEN"
                if verb in ["STOP", "EXIT", "KILL"]: verb = "CLOSE"
                if verb in ["WRITE"]: verb = "TYPE"
                if verb in ["REMOVE"]: verb = "DELETE"
                if verb in ["READ"]: verb = "EXCEL_READ"
                
                # Route ADD/GENERATE/CREATE/INSERT to DYNAMIC_CODE for complex operations
                if verb in ["ADD", "GENERATE", "CREATE", "INSERT"]:
                    complex_keywords = [
                        "dummy", "random", "fake", "sample", "test", 
                        "row", "rows", "data", "report", "analysis",
                        "excel", "spreadsheet", "sheet", "file", "values"
                    ]
                    
                    is_create_generate = verb in ["CREATE", "GENERATE"]
                    has_complex_keywords = any(kw in target.lower() for kw in complex_keywords)
                    
                    if is_create_generate or has_complex_keywords:
                        file_pattern_inner = r'[\w\-]+\.(xlsx|xls|csv)'
                        file_match_inner = re.search(file_pattern_inner, target, re.IGNORECASE)
                        
                        if file_match_inner:
                            file_name = file_match_inner.group(0)
                        else:
                            import time
                            timestamp = time.strftime("%Y%m%d_%H%M%S")
                            file_name = f"generated_{timestamp}.xlsx"
                        
                        task_desc = part
                        from execution.nlu import Command
                        fast_path_commands.append(Command(action="DYNAMIC_CODE", target=file_name, context=task_desc))
                        continue
                
                # COMPLEXITY CHECK for TYPE
                if verb == "TYPE":
                    is_quoted = False
                    if (target.startswith('"') and target.endswith('"')) or (target.startswith("'") and target.endswith("'")):
                        is_quoted = True
                        target = target[1:-1]
                    
                    if not is_quoted:
                        from execution.nlu import Command
                        fast_path_commands.append(Command(action=verb, target=target, context="GENERATE_ASYNC"))
                        continue
                
                # SPECIAL PARSING for RENAME and MOVE commands
                context = None
                if verb in ["RENAME", "MOVE"]:
                    rename_pattern = r"^(.+?)\s+(?:to|into)\s+(.+)$"
                    rename_match = re.match(rename_pattern, target, re.IGNORECASE)
                    
                    if rename_match:
                        target = rename_match.group(1).strip()
                        context = rename_match.group(2).strip()
                    else:
                        all_simple = False
                        break
                
                from execution.nlu import Command
                fast_path_commands.append(Command(action=verb, target=target, context=context))
            else:
                all_simple = False
                break
        
        if all_simple and fast_path_commands:
            commands = fast_path_commands
    
    # FALLBACK: Use DSPy NLU if no commands were extracted
    if not commands:
        try:
            commands = extract_commands(user_input)
        except Exception as e:
            commands = []
            steps.append({
                 "type": "Reasoning",
                 "content": f"NLU Error: {str(e)}",
                 "timestamp": datetime.now().strftime("%I:%M:%S %p")
            })


    # If NLU fails or returns empty (fallback)
    if not commands:
         steps.append({
            "type": "Reasoning",
            "content": f"No commands extracted from '{user_input}'",
            "timestamp": datetime.now().strftime("%I:%M:%S %p")
        })
         return {"messages": ["I didn't understand that command."], "intermediate_steps": steps}

    final_results = []
    
    # Optimizer: Merge OPEN + GENERATE_ASYNC
    # If we have [OPEN(app), TYPE(gen_async)], we remove OPEN, because execute_generative_command handles opening in parallel.
    optimized_commands = []
    skip_next = False
    
    for i in range(len(commands)):
        if skip_next:
            skip_next = False
            continue
            
        cmd = commands[i]
        
        # Look ahead
        if cmd.action in ["OPEN", "LAUNCH"] and i + 1 < len(commands):
            next_cmd = commands[i+1]
            if next_cmd.action in ["TYPE", "WRITE"] and next_cmd.context == "GENERATE_ASYNC":
                # Check if targets match? User might say "open notepad and type..."
                # Usually targets match or are implied.
                # We assume the TYPE command will pick up the app name from this OPEN command
                # But we need to pass the app name to the TYPE command context or target?
                # In the loop we did: `app_name = c.target` looking at `commands`.
                # If we remove it from `optimized_commands`, we need to ensure TYPE knows the app name.
                # Let's attach it to the next command's context or a new attribute?
                # or just set next_cmd.context = f"GENERATE_ASYNC:{cmd.target}"
                
                next_cmd.context = f"GENERATE_ASYNC:{cmd.target}"
                # content is already in next_cmd.target
                
                # Skip this OPEN command
                trace_logs = [] # We might miss logs if we skip
                # But we want parallelism.
                continue
        
        optimized_commands.append(cmd)
        
    commands = optimized_commands

    # 2. Execution Loop
    
    for cmd in commands:
        action = cmd.action.upper()
        target = cmd.target
        context = cmd.context
        
        # Consolidation: Collect all internal reasoning for this command here
        trace_logs = []
        
        result = ""
        tool_used = "None"
        attachment = None
        
        try:
            if action in ["OPEN", "LAUNCH", "PLAY", "VIEW", "SHOW", "GET", "SEARCH"]:
                tool_used = "Desktop Automation (Open)"
                
                # A. Try App Launch
                launch_res = launch_application(target)
                
                # B. Try File Search if App failed or if action implies file (view/play)
                file_path = None
                
                if "Could not find" in launch_res or "not in the system" in launch_res:
                    trace_logs.append(f"App launch failed. Searching for file '{target}'...")
                    
                    file_path = find_and_open_file(target)
                    
                    # Handle multiple files structured result
                    if isinstance(file_path, dict) and file_path.get("status") == "multiple_files":
                        result = file_path["message"]
                        # Generate options for UI
                        options = []
                        for f in file_path.get("files", []):
                            options.append({
                                "label": f"Open {os.path.basename(f)}",
                                "value": f"open {f}"
                            })
                        
                        # Attach options to the step (we'll do this when creating step_data)
                        attachment = {"type": "options", "data": options}
                    else:
                        result = file_path
                else:
                    result = launch_res

                # C. Check for Attachments (Media Playback)
                # If result looks like a file path and exists
                if file_path and "not found" not in str(file_path).lower() and "Found multiple" not in str(file_path) and os.path.exists(str(file_path)):
                    import mimetypes
                    import urllib.parse
                    
                    mime, _ = mimetypes.guess_type(str(file_path))
                    if mime:
                        media_type = None
                        if mime.startswith("image/"): media_type = "image"
                        elif mime.startswith("video/"): media_type = "video"
                        elif mime.startswith("audio/"): media_type = "audio"
                        
                        if media_type:
                            encoded_path = urllib.parse.quote(str(file_path))
                            file_url = f"http://localhost:8000/files/stream?path={encoded_path}"
                            
                            trace_logs.append(f"Displaying {media_type}: {os.path.basename(str(file_path))}")
                            
                            attachment = {
                                "type": media_type,
                                "url": file_url,
                                "name": os.path.basename(str(file_path))
                            }
                            result = f"Opened/Playing {os.path.basename(str(file_path))}"
                
                # WAIT for app to open!
                if "Launched" in result or "Opened" in result:
                     import time
                     trace_logs.append("Waiting 3s for app to focus...")
                     time.sleep(3) 

                     # HACK: Handle Office Apps (Word/Excel) stuck on Home Screen
                     tgt = target.lower()
                     if "word" in tgt or "excel" in tgt or "powerpoint" in tgt:
                         from capabilities.desktop import send_key
                         trace_logs.append("Sending ENTER to create New Document...")
                         send_key("enter")
                         time.sleep(1) # Wait for animation

            elif action in ["CLOSE", "STOP", "EXIT", "KILL"]:
                tool_used = "Desktop Automation (Close)"
                result = close_application(target)

            elif action in ["TYPE", "WRITE"]:
                tool_used = "Desktop Automation (Type)"
                
                # Context-Aware Generation (A1 Logic)
                is_async = False
                app_name = "Notepad" # Default
                
                if context and context.startswith("GENERATE_ASYNC"):
                     is_async = True
                     # Check if app name is embedded (e.g., GENERATE_ASYNC:notepad)
                     if ":" in context:
                         _, extracted_app = context.split(":", 1)
                         app_name = extracted_app.strip()
                     else:
                         # Fallback: Try to find open command in *original* steps? 
                         # But we optimized it away.
                         # If optimization didn't run (e.g. quoted text), we wouldn't be here.
                         pass
                
                if is_async or context == "GENERATE":
                     from execution.system_utils import execute_generative_command
                     import asyncio
                     
                     print(f"DEBUG: Triggering Parallel Execution for '{app_name}'...")
                     try:
                        result = asyncio.run(execute_generative_command(app_name, target))
                     except Exception as e:
                        result = f"Error in parallel execution: {e}"
                else:
                     # Literal typing (Fast Path quotes)
                     result = type_text(target)

            elif action in ["RENAME"]:
                tool_used = "Desktop Automation (Rename)"
                if context: 
                   result = rename_file(target, context)
                else:
                   result = "Error: New name not provided for rename."

            elif action in ["MOVE"]:
                tool_used = "Desktop Automation (Move)"
                if context:
                    result = move_file(target, context)
                else:
                    result = "Error: Destination not provided for move."

            elif action in ["DELETE", "REMOVE"]:
                tool_used = "Desktop Automation (Delete)"
                from capabilities.desktop import delete_file
                result = delete_file(target)

            elif action == "EXCEL_READ":
                tool_used = "Excel (Read)"
                # Target = File, Context = Sheet (Optional)
                file_path, _ = find_and_open_file(target).split("Opened: ") if "Opened: " in find_and_open_file(target) else (target, None)
                # If find_and_open returned a clean path, use it. But find_and_open opens it. 
                # We need a 'find_file' helper that doesn't open.
                # For now, let's assume target is path or we rely on validation.
                # Actually, reuse the internal search logic?
                # Let's just pass target to the capability and let it handle/fail.
                # Just incase, let's try to resolve the full path if it's just a filename
                if not os.path.exists(target) and not os.path.isabs(target):
                     found_paths = find_file_paths(target)
                     if found_paths: target = found_paths[0]

                result = read_sheet_data(target, sheet_name=context)

            elif action == "EXCEL_WRITE":
                tool_used = "Excel (Write Cell)"
                # Expect context to contain "sheet:Sheet1, cell:A1, value:10" or similar
                # Check for .xls conversion
                if not os.path.exists(target) and not os.path.isabs(target):
                     found_paths = find_file_paths(target)
                     if found_paths: target = found_paths[0]

                # Check for .xls conversion
                conversion_msg = ""
                if target.lower().endswith(".xls"):
                     new_target = convert_xls_to_xlsx(target)
                     if new_target:
                         target = new_target
                         conversion_msg = f" (Auto-converted to {os.path.basename(target)})"

                if context:
                    parts = [p.strip() for p in context.split(',')]
                    if len(parts) >= 3:
                        sheet, cell, val = parts[0], parts[1], ",".join(parts[2:])
                    elif len(parts) == 2:
                         sheet, cell, val = None, parts[0], parts[1]
                    else:
                        sheet, cell, val = None, "A1", context
                    
                    
                    # Capture Before State (HTML)
                    before_view = read_sheet_data(target, sheet_name=sheet, fmt="html")

                    result_action = write_cell(target, sheet, cell, val) + conversion_msg

                    # Capture After State (HTML)
                    after_view = read_sheet_data(target, sheet_name=sheet, fmt="html")
                    
                    result = f"""
                    <div class="excel-comparison">
                        <div>
                            <h4>Before Update</h4>
                            {before_view}
                        </div>
                        <div>
                            <h4>After Update</h4>
                            {after_view}
                        </div>
                    </div>
                    <p><strong>Action:</strong> {result_action}</p>
                    """
                else:
                    result = "Error: Context missing for Write (Cell, Value)."

            elif action == "EXCEL_ADD_ROW":
                tool_used = "Excel (Append Row)"
                # Context = "10, 20, 30"
                # Check for .xls conversion
                if not os.path.exists(target) and not os.path.isabs(target):
                     found_paths = find_file_paths(target)
                     if found_paths: target = found_paths[0]

                # Check for .xls conversion
                conversion_msg = ""
                if target.lower().endswith(".xls"):
                     new_target = convert_xls_to_xlsx(target)
                     if new_target:
                         target = new_target
                         conversion_msg = f" (Auto-converted to {os.path.basename(target)})"

                if context:
                    # Smart Parsing: Check for key-value pairs (e.g., "name is raj, age=20")
                    data = None
                    if any(sep in context for sep in ["=", " is ", ":"]):
                        try:
                            data_dict = {}
                            # Split by comma first (arguments separator)
                            # Also handle " and " if it hasn't been split by upstream NLU
                            raw_args = re.split(r",|\s+and\s+", context)
                            
                            for arg in raw_args:
                                arg = arg.strip()
                                if not arg: continue
                                
                                key, val = None, None
                                if "=" in arg:
                                    key, val = arg.split("=", 1)
                                elif " is " in arg:
                                    key, val = arg.split(" is ", 1)
                                elif ":" in arg:
                                    key, val = arg.split(":", 1)
                                
                                if key and val:
                                    data_dict[key.strip()] = val.strip()
                            
                            if data_dict:
                                data = data_dict
                        except:
                            pass # Fallback to list if parsing fails

                    if data is None:
                        # Fallback: Treat as ordered list
                        data = [d.strip() for d in context.split(',')]
                    
                    # Capture Before State (HTML)
                    before_view = read_sheet_data(target, fmt="html")

                    result_action = append_row(target, None, data) + conversion_msg

                    # Capture After State (HTML)
                    after_view = read_sheet_data(target, fmt="html")

                    result = f"""
                    <div class="excel-comparison">
                        <div>
                            <h4>Before Update</h4>
                            {before_view}
                        </div>
                        <div>
                            <h4>After Update</h4>
                            {after_view}
                        </div>
                    </div>
                    <p><strong>Action:</strong> {result_action}</p>
                    """
                else:
                    result = "Error: Context missing for Append Row (Data)."

            elif action == "EXCEL_DELETE_ROW":
                tool_used = "Excel (Delete Row)"
                # Context = "5" (Row index) or "last row"
                if not os.path.exists(target) and not os.path.isabs(target):
                     found_paths = find_file_paths(target)
                     if found_paths: target = found_paths[0]

                try:
                    idx = 0
                    c_low = context.strip().lower() if context else ""
                    
                    if "last" in c_low:
                         # Resolve "last row" by opening file
                         try:
                             import openpyxl
                             wb = openpyxl.load_workbook(target)
                             ws = wb.active # TODO: Support generic sheet if specified? For now active.
                             idx = ws.max_row
                             trace_logs.append(f"Resolved 'last row' to index {idx}")
                         except Exception as e:
                             result = f"Error resolving last row: {str(e)}"
                             idx = -1
                    else:
                        idx = int(convert_to_number(context)) if context else 0 # Helper or just int?
                        # Fallback to simple int parsing
                        digits = ''.join(filter(str.isdigit, context or ""))
                        if digits: idx = int(digits)
                    
                    if idx > 0:
                        # Capture Before State (HTML)
                        before_view = read_sheet_data(target, fmt="html")
                        
                        result_action = delete_row(target, None, idx)
                        
                        # Capture After State (HTML)
                        after_view = read_sheet_data(target, fmt="html")

                        result = f"""
                        <div class="excel-comparison">
                            <div>
                                <h4>Before Update</h4>
                                {before_view}
                            </div>
                            <div>
                                <h4>After Update</h4>
                                {after_view}
                            </div>
                        </div>
                        <p><strong>Action:</strong> {result_action}</p>
                        """
                    elif idx != -1:
                        result = "Error: Invalid row index."
                except Exception as e:
                    result = f"Error interpreting row index: {str(e)}"

            elif action == "EXCEL_STYLE":
                tool_used = "Excel (Style)"
                # Context = "A1, red" or "A1, red, white, bold"
                if not os.path.exists(target) and not os.path.isabs(target):
                     found_paths = find_file_paths(target)
                     if found_paths: target = found_paths[0]

                if context:
                    parts = [p.strip() for p in context.split(',')]
                    # simple parsing: Cell, Color, Border
                    if len(parts) >= 2:
                        cell = parts[0]
                        color = parts[1]
                        # Check for keywords
                        is_bold = "bold" in context.lower()
                        has_border = "border" in context.lower()
                        
                        # Capture Before State (HTML)
                        before_view = read_sheet_data(target, fmt="html")

                        result_action = set_style(target, None, cell, bg_color=color, bold=is_bold, border=has_border)

                        # Capture After State (HTML)
                        after_view = read_sheet_data(target, fmt="html")

                        result = f"""
                        <div class="excel-comparison">
                            <div>
                                <h4>Before Update</h4>
                                {before_view}
                            </div>
                            <div>
                                <h4>After Update</h4>
                                {after_view}
                            </div>
                        </div>
                        <p><strong>Action:</strong> {result_action}</p>
                        """
                    else:
                         result = "Error: Context requires 'Cell, Color'."

            elif action == "EXCEL_REFRESH_PIVOTS":
                tool_used = "Excel (Refresh Pivots)"
                from capabilities.excel_manipulation import enable_pivot_table_refresh
                
                if not os.path.exists(target) and not os.path.isabs(target):
                     found_paths = find_file_paths(target)
                     if found_paths: target = found_paths[0]
                
                result = enable_pivot_table_refresh(target)

            elif action == "DOC_REPORT":
                tool_used = "Document Intelligence (Report)"
                from capabilities.report_generator import generate_report_from_data
                
                task_desc = context if context else user_input
                target_file = target
                
                # ── Robust File Resolution ──
                if not os.path.exists(target_file):
                    # 1. Try find_file_paths (uses search index)
                    if not os.path.isabs(target_file):
                        found = find_file_paths(target_file)
                        if found: target_file = found[0]
                    
                    # 2. Try alternative extension (.xls ↔ .xlsx)
                    if not os.path.exists(target_file):
                        base, ext = os.path.splitext(target_file)
                        alt_name = None
                        if ext.lower() == '.xlsx':
                            alt_name = os.path.basename(base) + '.xls'
                        elif ext.lower() == '.xls':
                            alt_name = os.path.basename(base) + '.xlsx'
                        
                        if alt_name:
                            found = find_file_paths(alt_name)
                            if found: target_file = found[0]
                    
                    # 3. Search common user directories
                    if not os.path.exists(target_file):
                        home = os.path.expanduser("~")
                        search_dirs = [
                            os.path.join(home, "Desktop"),
                            os.path.join(home, "Documents"),
                            os.path.join(home, "Downloads"),
                            home,
                        ]
                        fname = os.path.basename(target)
                        fname_base = os.path.splitext(fname)[0]
                        
                        for d in search_dirs:
                            if not os.path.isdir(d):
                                continue
                            for f in os.listdir(d):
                                if f.lower() == fname.lower() or os.path.splitext(f)[0].lower() == fname_base.lower():
                                    target_file = os.path.join(d, f)
                                    break
                            if os.path.exists(target_file):
                                break
                    
                    print(f"[DOC_REPORT] Resolved file: {target_file} (exists={os.path.exists(target_file)})")
                
                trace_logs.append(f"Generating structured report for: {task_desc}")
                
                # Capture Before State (source data preview)
                before_view = ""
                if os.path.exists(target_file):
                    before_view = read_sheet_data(target_file, fmt="html")
                
                # Execute S1 Pipeline
                report_result = generate_report_from_data(task=task_desc, file_path=target_file)
                
                if report_result["status"] == "success":
                    output_path = report_result["output_path"]
                    summary = report_result["summary"]
                    
                    result = f"""
                    <div class="excel-comparison">
                        <div>
                            <h4>Source Data</h4>
                            {before_view}
                        </div>
                    </div>
                    <p><strong>✅ {summary}</strong></p>
                    <p>📄 Saved to: <code>{output_path}</code></p>
                    """
                    
                    # Attach as downloadable file
                    if output_path and os.path.exists(output_path):
                        import urllib.parse
                        encoded_path = urllib.parse.quote(output_path)
                        attachment = {
                            "type": "file",
                            "url": f"http://localhost:8000/files/stream?path={encoded_path}",
                            "name": os.path.basename(output_path)
                        }
                else:
                    error_msg = report_result.get("error", "Unknown error")
                    result = f"❌ Report generation failed: {error_msg}"

            elif action == "DYNAMIC_CODE":
                tool_used = "Dynamic AI Coder"
                from capabilities.code_generator import generate_and_run_script
                
                # Context usually contains the task desc
                task_desc = context if context else "Perform the requested operation"
                
                # Check for file target
                target_file = target
                
                # Smart File Detection
                if target_file == "active_workbook" or (not os.path.exists(target_file) and "." not in target_file):
                     # Try to find file in context by looking for tokens ending in .xlsx/.xls/.csv
                     # This avoids greedy regex matching the entire sentence
                     potential_files = [w.strip("',\"") for w in task_desc.split() if w.lower().endswith(('.xlsx', '.xls', '.csv'))]
                     if potential_files:
                         # Use the last one found? or first? usually file is at end.
                         target_file = potential_files[-1]
                     else:
                         # Fallback Regex for filenames with spaces if quoted?
                         import re
                         quoted = re.search(r'["\']([^"\']+\.(xlsx|xls|csv))["\']', task_desc, re.IGNORECASE)
                         if quoted:
                             target_file = quoted.group(1)
                
                # Resolve path
                if not os.path.exists(target_file) and not os.path.isabs(target_file):
                     found = find_file_paths(target_file)
                     if found: target_file = found[0]
                
                trace_logs.append(f"Generating custom script for: {task_desc} on {target_file}")
                
                # Excel/File Preview logic
                is_excel = target_file.lower().endswith(('.xls', '.xlsx', '.csv'))
                before_view = ""
                if is_excel and os.path.exists(target_file):
                    before_view = read_sheet_data(target_file, fmt="html")
                
                # EXECUTE
                script_result = generate_and_run_script(task=task_desc, file_path=target_file)
                
                if is_excel and os.path.exists(target_file):
                    # Capture After State
                    after_view = read_sheet_data(target_file, fmt="html")
                    
                    result = f"""
                    <div class="excel-comparison">
                        <div>
                            <h4>Before Update</h4>
                            {before_view}
                        </div>
                        <div>
                            <h4>After Update</h4>
                            {after_view}
                        </div>
                    </div>
                    <div>{script_result}</div>
                    """
                else:
                    result = script_result

            else:
                result = f"Action '{action}' not implemented yet."
        
        except Exception as e:
            result = f"Error executing {action}: {str(e)}"
            
        final_results.append(result)

        # Create Unified Block Content
        block_content = f"**Task:** {action} {target}"
        if context:
            block_content += f" (in {context})"
            
        if trace_logs:
            # Add traces as a small list
            block_content += "\n" + "\n".join([f"- {Log}" for Log in trace_logs])
            
        block_content += f"\n**Result:** {result}"
        
        step_data = {
            "type": "Action",
            "content": block_content,
            "timestamp": datetime.now().strftime("%I:%M:%S %p")
        }
        
        if attachment:
            step_data["attachment"] = attachment
            
        steps.append(step_data)
    
    return {"messages": final_results, "intermediate_steps": steps}

# 4. Define Graph
workflow = StateGraph(AgentState)

workflow.add_node("agent", execute_tool) # Simplified for brevity
workflow.set_entry_point("agent")
workflow.add_edge("agent", END)

app = workflow.compile()


async def run_agent(user_input: str):
    inputs = {"input": user_input, "messages": []}
    result = await app.ainvoke(inputs)
    # Extract steps from the last node execution
    # In LangGraph, we might need to adjust how we pass this back.
    # For now, we return the 'intermediate_steps' from the state.
    return {"steps": result.get("intermediate_steps", [])}
