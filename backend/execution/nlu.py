import re
import urllib.parse
import time
import json
import ast
import dspy
from typing import List, Optional
from pydantic import BaseModel, Field

class Command(BaseModel):
    action: str = Field(description="One of: EXCEL_READ, EXCEL_WRITE, EXCEL_ADD_ROW, EXCEL_DELETE_ROW, EXCEL_STYLE, EXCEL_REFRESH_PIVOTS, DYNAMIC_CODE, DOC_REPORT, ANSWER, WEB_CONTROL, OPEN, CLOSE, RENAME, MOVE, DELETE.")
    target: str = Field(description="The FILE PATH or APP NAME for the action. For EXCEL actions, this MUST be the filename.")
    context: Optional[str] = Field(None, description="The details or parameters (e.g., 'A1, red', 'headers, blue').")
    reasoning: Optional[str] = Field(None, description="Internal reasoning for this command.")

class SimpleIntent(dspy.Signature):
    """
    Carefully read the user input and the chat history. 
    Extract the INTENT of the user and represent it as a list of system actions.
    
    SPECIAL CASE (LATENCY OPTIMIZATION):
    If the user's intent is a query for information, facts, news, stock data, or creative writing (ANSWER action):
    1. Set action to 'ANSWER'.
    2. Provide the FULL, FINAL, COMPLETE ACTUAL ANSWER or generated content directly in the 'direct_answer' field.
    3. MANDATORY: You MUST provide the answer content itself (e.g., "The history of India begins..."). 
    4. FORBIDDEN: NEVER use meta-commentary or planning language like "I will search...", "I will look for...", "Searching for...", "I can help with...".
    5. FORBIDDEN: NEVER mention browsers, tools, or internal processes. Just give the facts.
    6. Ignore any "DEBUG" or "Traceback" logs in the context; do not repeat them.
    
    System Actions (ONLY USE THESE):
    - EXCEL_<ACTION>: Spreadsheet operations on EXISTING Excel files.
    - ANSWER <query>: General info retrieval (facts, explanations, creative writing).
    - DYNAMIC_CODE <task>: Complex tasks that require GENERATING AND EXECUTING code.
      - USE THIS for: data retrieval (stock prices, exchange rates, web scraping),
        creating NEW Excel files with data, complex analysis, calculations,
        any task that combines fetching data + saving to files.
      - Target: filename (e.g., 'nikkei_data.xlsx') or 'auto' if creating new file.
      - Context: Full task description.
    - WEB_CONTROL <site/task>: Browser automation (navigate, search, click, filter).
      - USE THIS for ANY request involving VISITING a website with a browser.
      - COMBINE multiple steps into a SINGLE `WEB_CONTROL` command.
      - Target: The website URL or Name. Context: The full description of the task.
    - OPEN <app/file>: Launch application or open file (e.g., 'notepad', 'data.xlsx').
    - CLOSE <app>: Close an application (e.g., 'notepad', 'chrome').
    - DELETE <file>: Delete a file (e.g., 'old_data.csv').
    - RENAME <file>: Rename file (Target=old, Context=new name).
    - MOVE <file>: Move file (Target=file, Context=destination folder).
    - DOC_REPORT: Generate reports from data files.

    CRITICAL: 
    - NEVER use action-like strings as the 'target'. 
    - WRONG: target='open_file', target='select_range', target='set_red_color'.
    - RIGHT: target='gendata.xlsx', target='Google Chrome'.
    - If the user wants to style a file, target should be the FILE NAME, and context should be the STYLE details.
    - If the user wants to perform a WEB TASK, use `WEB_CONTROL`. Do NOT split into OPEN/TYPE/CLICK.
    """
    chat_history: str = dspy.InputField(desc="Previous context. Do NOT repeat or reference any logs/system state.")
    user_input: str = dspy.InputField(desc="User's natural language command")
    reasoning: str = dspy.OutputField(desc="Internal reasoning (concise).")
    direct_answer: str = dspy.OutputField(desc="The FINAL FACTUAL CONTENT. No 'I will' language.")
    commands_json: str = dspy.OutputField(desc="JSON list of commands. ONLY use the actions listed above.")

predictor = dspy.Predict(SimpleIntent)

class DirectAnswer(dspy.Signature):
    """Answer the user's question directly and concisely."""
    question = dspy.InputField()
    answer = dspy.OutputField()

class RawResponse(dspy.Signature):
    """Output the response exactly as requested, without any prefixes or formatting."""
    prompt = dspy.InputField()
    response = dspy.OutputField()

answer_generator = dspy.Predict(DirectAnswer)
raw_generator = dspy.Predict(RawResponse)

def generate_text_content(prompt: str) -> str:
    try:
        pred = answer_generator(question=prompt)
        return pred.answer
    except Exception as e:
        print(f"Error generating text content: {e}")
        return f"Error generating content: {e}"

def generate_raw_response(prompt: str) -> str:
    try:
        pred = raw_generator(prompt=prompt)
        return pred.response
    except Exception as e:
        print(f"Error generating raw response: {e}")
        return f"Error: {e}"

def extract_commands(text: str, chat_history: str = "") -> List[Command]:
    clean_text = text.strip()
    print(f"DEBUG NLU: Consulting LLM for '{clean_text}'")
    
    for attempt in range(2):
        try:
            prediction = predictor(chat_history=chat_history, user_input=clean_text)
            
            json_str = getattr(prediction, 'commands_json', '')
            print(f"DEBUG NLU RAW RESPONSE: {json_str[:500]}...", flush=True)
            reasoning = getattr(prediction, 'reasoning', '')
            direct_answer = getattr(prediction, 'direct_answer', '')
            if direct_answer: print(f"DEBUG NLU DIRECT ANSWER: {direct_answer[:50]}...", flush=True)
            
            # 1. Cleanup Markdown and JSON fragments
            if "```" in json_str:
                if "json" in json_str:
                    json_str = json_str.split("```json")[1].split("```")[0].strip()
                else:
                    json_str = json_str.split("```")[1].split("```")[0].strip()
            
            # 2. Parse Raw Data
            raw_data = None
            try:
                raw_data = json.loads(json_str)
            except:
                try:
                    raw_data = ast.literal_eval(json_str)
                except:
                    try:
                        fixed = json_str.replace("'", '"')
                        raw_data = json.loads(fixed)
                    except:
                        pass
            
            if not raw_data:
                if direct_answer:
                    print(f"DEBUG NLU: No JSON commands, but direct_answer found. Synthesizing ANSWER.", flush=True)
                    return [Command(action="ANSWER", target=clean_text, context=f"FINAL_ANSWER:{direct_answer}", reasoning=reasoning)]
                if attempt == 0:
                    clean_text += "\n\nCRITICAL: Your output must be VALID JSON. Try again."
                    continue
                return []

            # 3. Normalize List
            cmds_list = []
            if isinstance(raw_data, list):
                cmds_list = raw_data
            elif isinstance(raw_data, dict):
                if "commands" in raw_data and isinstance(raw_data["commands"], list):
                    cmds_list = raw_data["commands"]
                else:
                    is_command_like = any(k in raw_data for k in ["action", "command", "tool_name", "type", "intent"])
                    if is_command_like:
                        cmds_list = [raw_data]
                    else:
                        print(f"DEBUG NLU: LLM outputted raw content. wrapping in ANSWER.", flush=True)
                        content = raw_data.get("answer", raw_data.get("poem", json.dumps(raw_data, indent=2)))
                        return [Command(action="ANSWER", target=text, context=content, reasoning=reasoning)]

            final_cmds = []
            print(f"DEBUG NLU: Processing {len(cmds_list)} items", flush=True)
            
            # 0. WEB TASK CONSOLIDATION CHECK
            # Detect ANY web-related intent and force it into a single WEB_CONTROL command.
            # The handler has the site-map and will resolve URLs.
            clean_lower = clean_text.lower()
            web_triggers = ["go to", "navigate to", "open website", "browse", "log in to", "login to",
                            "search on", "visit", "go on", "open amazon", "open google", "open gmail",
                            "open flipkart", "open youtube", "open github", "open facebook"]
            web_actions = ["and click", "then click", "search for", "and type", "and search",
                           "and login", "and log in", "click the", "fill the", "enter the"]
            
            is_web = False
            # Check for explicit URL
            if re.search(r'(https?://|www\.)', clean_text):
                is_web = True
            # Check for web trigger keywords
            elif any(k in clean_lower for k in web_triggers):
                is_web = True
            # Check for combined nav+action
            elif any(k in clean_lower for k in ["go to", "navigate"]) and \
                 any(k in clean_lower for k in web_actions):
                is_web = True
            
            if is_web:
                # Extract a target (URL or site name)
                url_match = re.search(r'(https?://[^\s]+|www\.[^\s]+)', clean_text)
                if url_match:
                    target = url_match.group(0)
                else:
                    # Extract site name from "go to X" or "open X"
                    site_match = re.search(r'(?:go to|navigate to|open|visit|log ?in to|browse)\s+(\w+)', clean_lower)
                    target = site_match.group(1) if site_match else clean_text
                
                print(f"DEBUG NLU: WEB task detected → WEB_CONTROL target='{target}', context='{clean_text}'")
                return [Command(action="WEB_CONTROL", target=target, context=clean_text)]

            for c in cmds_list:
                if not isinstance(c, dict): 
                    final_cmds.append(Command(action="ANSWER", target=str(c)))
                    continue
                
                # A. Raw Extraction
                action_keys = ["action", "command", "tool_name", "type", "intent"]
                r_action = ""
                for k in action_keys:
                    if k in c:
                        r_action = str(c[k]).lower()
                        break
                
                r_target = ""
                for k in ["target", "action_input", "input", "query", "url", "website", "filename", "file", "text"]:
                    if k in c and c[k]:
                        r_target = str(c[k]).strip()
                        # Strip prefixes like "file_path:", "app:", "target:" and common verbs/articles RECURSIVELY
                        while True:
                            new_target = re.sub(r'^([\w_]+[:=]|open|launch|get|show|view|find|the|a|an)\s+', '', r_target, flags=re.IGNORECASE).strip()
                            if new_target == r_target: break
                            r_target = new_target
                        break
                
                r_context = str(c.get("context", ""))
                params = c.get("parameters", {})
                if isinstance(params, dict):
                    if not r_target:
                        for k in ["url", "website", "query", "target"]:
                            if k in params: 
                                r_target = re.sub(r'^([\w_]+[:=]|open|launch|get|show|view|find)\s*', '', str(params[k]), flags=re.IGNORECASE)
                                break
                    if not r_context:
                        r_context = " ".join([f"{k}:{v}" for k,v in params.items()])

                # B. Normalization
                norm_action = r_action.upper().replace(" ", "_").replace(".", "_")
                f_action = "OPEN" # Default
                
                # De-hallucination: Fuzzy check for tool names
                # If target has underscores and NO extension, it's likely a hallucination
                is_file_like = "." in r_target and len(r_target.split(".")[-1]) in [2, 3, 4]
                looks_like_tool = "_" in r_target and not is_file_like
                
                hallucinated_tools = ["open_file", "select_range", "set_cell_color", "get_file", "find_file", "style_header", "color_columns", "format_sheet", "format_excel_column_names"]
                if r_target.lower() in hallucinated_tools or looks_like_tool:
                    print(f"DEBUG NLU: Detected hallucinated tool in target: '{r_target}'. Cleaning up.")
                    if any(kw in r_target.lower() for kw in ["style", "color", "format", "font"]):
                        norm_action = "EXCEL_STYLE"
                    r_target = "" 
                
                SUPPORTED = [
                    "OPEN", "CLOSE", "TYPE", "RENAME", "MOVE", "DELETE", 
                    "EXCEL_READ", "EXCEL_WRITE", "EXCEL_ADD_ROW", "EXCEL_DELETE_ROW", 
                    "EXCEL_STYLE", "EXCEL_REFRESH_PIVOTS", "DYNAMIC_CODE", "DOC_REPORT", "ANSWER",
                    "WEB_CONTROL"
                ]
                
                if norm_action in SUPPORTED:
                    f_action = norm_action
                else:
                    if any(kw in norm_action for kw in ["EXCEL", "SHEET", "ROW", "CELL", "COLUMN"]):
                        if "READ" in norm_action: f_action = "EXCEL_READ"
                        elif "ADD" in norm_action or "APPEND" in norm_action: f_action = "EXCEL_ADD_ROW"
                        elif "DELETE" in norm_action or "REMOVE" in norm_action: f_action = "EXCEL_DELETE_ROW"
                        elif any(kw in norm_action for kw in ["STYLE", "COLOR", "FORMAT", "FONT", "BORDER"]): f_action = "EXCEL_STYLE"
                        else: f_action = "EXCEL_WRITE"
                    elif any(kw in norm_action for kw in ["CODE", "SCRIPT", "PYTHON", "RUN", "EXECUTE", "CALCULATE", "ANALYZE", "AUTOMATE"]):
                        f_action = "DYNAMIC_CODE"
                    elif any(kw in norm_action for kw in ["ANSWER", "TELL", "EXPLAIN", "SEARCH", "INFO", "QUESTION"]):
                        f_action = "ANSWER"
                    elif any(kw in norm_action for kw in ["TYPE", "WRITE", "INPUT"]):
                        f_action = "TYPE"
                    elif any(kw in norm_action for kw in ["WEB", "BROWSER", "LOGIN", "CLICK", "NAVIGATE", "GO TO", "SITE"]):
                        f_action = "WEB_CONTROL"

                # C. Final Refinements
                # 1. Recovery: If target is empty or invalid, find a file in the input text
                if not r_target or r_target.lower() in hallucinated_tools or looks_like_tool:
                    file_match = re.search(r'([\w\-\. \d]+\.(xlsx|xls|csv|txt|pdf|docx|exe|lnk))', clean_text, re.IGNORECASE)
                    if file_match:
                        raw_match = file_match.group(1).strip()
                        while True:
                            cleaned_match = re.sub(r'^(open|launch|get|show|view|find|the|a|an)\s+', '', raw_match, flags=re.IGNORECASE).strip()
                            if cleaned_match == raw_match: break
                            raw_match = cleaned_match
                        r_target = raw_match
                        print(f"DEBUG NLU: Recovered and cleaned target '{r_target}' from input text.")

                # 2. SEMANTIC RECOVERY: If action is EXCEL_STYLE but context is missing info, pull from raw text
                if f_action == "EXCEL_STYLE":
                    t_low = str(r_target).lower()
                    c_low = str(r_context).lower()
                    
                    # Ensure "red", "blue" etc are in context if mentioned in prompt
                    colors = ["red", "blue", "green", "yellow", "black", "white", "orange", "pink"]
                    target_objs = ["header", "column", "row", "names", "first row"]
                    
                    found_colors = [c for c in colors if c in clean_text.lower()]
                    found_objs = [o for o in target_objs if o in clean_text.lower()]
                    
                    if found_colors and not any(c in c_low for c in found_colors):
                        r_context = f"{r_context}, {found_colors[0]}".strip(", ")
                    if found_objs and not any(o in c_low or o in t_low for o in found_objs):
                        r_context = f"{found_objs[0]}, {r_context}".strip(", ")

                # 3. Swap target/context if action is EXCEL style/write and target looks like style info
                if f_action.startswith("EXCEL_") and f_action != "EXCEL_READ":
                    t_low = str(r_target).lower()
                    has_file_in_target = any(ext in t_low for ext in [".xlsx", ".xls", ".csv"])
                    has_file_in_context = any(ext in str(r_context).lower() for ext in [".xlsx", ".xls", ".csv"])
                    
                    if not has_file_in_target and has_file_in_context:
                        r_target, r_context = r_context, r_target
                    elif not has_file_in_target and not has_file_in_context:
                        if any(kw in t_low for kw in ["red", "blue", "green", "color", "header", "column", "row", "A1", "B2"]):
                            r_context = f"{r_target}, {r_context}".strip(", ")
                            file_match = re.search(r'[\w\-\. \d]+\.(xlsx|xls|csv)', clean_text, re.IGNORECASE)
                            r_target = file_match.group(0).strip() if file_match else ""

                if f_action == "OPEN" and len(r_target.split()) > 3 and not any(ext in r_target.lower() for ext in [".exe", ".lnk", ".txt", ".pdf", ".xlsx", ".xls", ".csv"]):
                    f_action = "ANSWER"
                
                if f_action == "ANSWER" and direct_answer:
                    r_context = f"FINAL_ANSWER:{direct_answer}"
                elif f_action == "DYNAMIC_CODE" and not r_context:
                    r_context = r_target if len(r_target) > 5 else clean_text

                print(f"DEBUG NLU MAPPING: r_action='{r_action}', f_action='{f_action}', target='{r_target}', context='{r_context}'", flush=True)

                cmd_obj = Command(
                    action=f_action,
                    target=r_target or r_action,
                    context=r_context
                )
                if not final_cmds: cmd_obj.reasoning = reasoning
                final_cmds.append(cmd_obj)
            
            if final_cmds: return final_cmds
            
        except Exception as e:
            print(f"DEBUG NLU FAILURE: {e}")
            if attempt == 0: continue
            
    return []

def fast_path_extract(user_input: str) -> List[Command]:
    """
    Rapidly extracts commands using regex patterns for common interactions.
    """
    user_input = user_input.lower().strip()
    
    # Standard Verb-Target Pattern
    simple_pattern = r"^\s*(open|launch|play|view|show|get|search|close|stop|exit|kill|type|write|set|delete|remove|rename|move|add|generate|create|insert|read|find|filter|who|what|which|list|count|extract|retrieve|scrape)\s+(.+)$"
    match = re.match(simple_pattern, user_input)
    
    if match:
        verb, target = match.group(1).upper(), match.group(2).strip()
        
        # 0. WEB CONTROL Priority
        # If target is a URL or has "http", force WEB_CONTROL
        if "http" in target or target.startswith("www."):
            return [Command(action="WEB_CONTROL", target=target, context="Navigate")]

        # Mapping Verbs to Actions
        action_map = {
            "LAUNCH": "OPEN", "PLAY": "OPEN", "VIEW": "OPEN", "SHOW": "OPEN", "GET": "OPEN",
            "STOP": "CLOSE", "EXIT": "CLOSE", "KILL": "CLOSE",
            "WRITE": "TYPE", "INSERT": "TYPE",
            "REMOVE": "DELETE",
            "SEARCH": "ANSWER", "FIND": "ANSWER", "FILTER": "ANSWER",
            "EXTRACT": "ANSWER", "RETRIEVE": "ANSWER", "SCRAPE": "ANSWER"
        }
        verb = action_map.get(verb, verb)
        
        # STRIP REDUNDANT VERBS/ARTICLES FROM TARGET
        target = re.sub(r'^(open|launch|get|show|view|find|the|a|an)\s+', '', target, flags=re.IGNORECASE)
        
        # Query Parsing (Re-routed to ANSWER)
        if verb == "ANSWER":
            web_target = target
            for kw in ["from web", "online", "the info", "information", "info about"]:
                web_target = web_target.replace(kw, "").strip()
            
            # If target only contained keywords, use original input as query
            if not web_target or len(web_target) < 2:
                web_target = user_input.replace("extract", "").replace("from web", "").replace("online", "").strip()
            
            return [Command(action="ANSWER", target=web_target)]
        
        # 3. WEB_CONTROL if target is URL
        if "http" in target or target.startswith("www."):
            return [Command(action="WEB_CONTROL", target=target, context="Navigate")]

        return [Command(action=verb, target=target)]
        
    return []

def get_commands(text: str, chat_history: str = "") -> List[Command]:
    """
    Unified entry point for command extraction. 
    Tries Fast Path first for simple commands, then fallback to LLM.
    """
    lower = text.lower().strip()
    
    # ===== 0a. PRE-LLM DATA TASK INTERCEPT (HIGHEST PRIORITY) =====
    # Compound tasks: retrieve data + create file → route to DYNAMIC_CODE
    data_keywords = ["retrieve", "fetch", "stock", "closing value", "opening value",
                     "exchange rate", "currency rate", "gold price", "silver price",
                     "nikkei", "sensex", "nifty", "s&p", "dow jones", "nasdaq",
                     "bitcoin", "crypto", "market data", "stock average",
                     "closing price", "opening price", "share price"]
    file_keywords = ["excel", "xlsx", "csv", "spreadsheet", "file", "save", "input",
                     "create a new", "put in", "store", "write to"]
    has_data_kw = any(kw in lower for kw in data_keywords)
    has_file_kw = any(kw in lower for kw in file_keywords)
    
    if has_data_kw and has_file_kw:
        # This is a compound data retrieval + file creation task
        # Extract filename if mentioned
        file_match = re.search(r'([\w-]+\.(?:xlsx|xls|csv))', lower)
        target_file = file_match.group(1) if file_match else "retrieved_data.xlsx"
        print(f"DEBUG NLU: PRE-LLM DATA INTERCEPT → DYNAMIC_CODE target='{target_file}', context='{text}'")
        return [Command(action="DYNAMIC_CODE", target=target_file, context=text)]
    
    # Also route pure data retrieval without file mention to DYNAMIC_CODE
    if has_data_kw and any(kw in lower for kw in ["round", "decimal", "last 10", "previous", "past"]):
        print(f"DEBUG NLU: PRE-LLM DATA INTERCEPT → DYNAMIC_CODE (data retrieval)")
        return [Command(action="DYNAMIC_CODE", target="data_output.xlsx", context=text)]

    # ===== 0b. PRE-LLM DESKTOP INTERCEPT =====
    # Catch desktop commands BEFORE the web intercept to prevent hijacking
    desktop_verbs = ["close ", "kill ", "stop ", "exit ", "rename ", "move ", "delete ", "remove "]
    is_desktop_verb = any(lower.startswith(v) for v in desktop_verbs)
    
    # "open X" is desktop UNLESS X is a known website or URL
    is_open_cmd = lower.startswith("open ") or lower.startswith("launch ")
    if is_open_cmd:
        open_target = re.sub(r'^(open|launch)\s+', '', lower).strip()
        open_target = re.sub(r'^(the|a|an)\s+', '', open_target).strip()
        # Only treat as desktop if target is NOT a known website/URL
        target_is_web = (
            bool(re.search(r'(https?://|www\.)', open_target)) or
            bool(re.search(r'\b\w+\.(com|org|net|io|in|co\.in|edu|gov|co|me|app)\b', open_target))
        )
        if not target_is_web:
            # Check it's not in known_sites list below
            known_sites_for_check = ["wikipedia", "amazon", "google", "gmail", "youtube", "github",
                       "facebook", "twitter", "linkedin", "flipkart", "instagram",
                       "reddit", "stackoverflow", "netflix", "spotify", "myntra",
                       "meesho", "ajio", "swiggy", "zomato", "paytm",
                       "imdb", "snapdeal", "irctc"]
            if not any(site in open_target for site in known_sites_for_check):
                print(f"DEBUG NLU: DESKTOP INTERCEPT → OPEN target='{open_target}'")
                return [Command(action="OPEN", target=open_target)]
    
    if is_desktop_verb:
        # Parse verb + target from input
        parts = lower.split(None, 1)
        if len(parts) >= 2:
            verb = parts[0].upper()
            dtarget = parts[1].strip()
            # Map synonyms
            verb_map = {"KILL": "CLOSE", "STOP": "CLOSE", "EXIT": "CLOSE", "REMOVE": "DELETE"}
            verb = verb_map.get(verb, verb)
            
            # For RENAME: parse "X to Y"
            if verb == "RENAME" and " to " in dtarget:
                old, new = dtarget.split(" to ", 1)
                print(f"DEBUG NLU: DESKTOP INTERCEPT → RENAME target='{old.strip()}', context='{new.strip()}'")
                return [Command(action="RENAME", target=old.strip(), context=new.strip())]
            
            # For MOVE: parse "X to Y"
            if verb == "MOVE" and " to " in dtarget:
                src, dest = dtarget.split(" to ", 1)
                print(f"DEBUG NLU: DESKTOP INTERCEPT → MOVE target='{src.strip()}', context='{dest.strip()}'")
                return [Command(action="MOVE", target=src.strip(), context=dest.strip())]
            
            print(f"DEBUG NLU: DESKTOP INTERCEPT → {verb} target='{dtarget}'")
            return [Command(action=verb, target=dtarget)]
    
    # ===== 0c. PRE-LLM WEB INTERCEPT =====
    # If the input contains a URL or known website name, ALWAYS route to WEB_CONTROL.
    has_url = bool(re.search(r'(https?://|www\.)', text))
    
    # Check for domain extensions (catches "myntra.com", "amazon.in", etc.)
    has_domain = bool(re.search(r'\b\w+\.(com|org|net|io|in|co\.in|edu|gov|co|me|app)\b', lower))
    
    known_sites = ["wikipedia", "amazon", "google", "gmail", "youtube", "github",
                   "facebook", "twitter", "linkedin", "flipkart", "instagram",
                   "reddit", "stackoverflow", "netflix", "spotify", "myntra",
                   "meesho", "ajio", "swiggy", "zomato", "paytm",
                   "imdb", "snapdeal", "irctc", "weather", "example"]
    has_site = any(site in lower for site in known_sites)
    
    web_verbs = ["go to", "navigate to", "open website", "browse to", "visit",
                 "log in to", "login to", "sign in to", "search on"]
    has_web_verb = any(v in lower for v in web_verbs)
    
    if has_url or has_domain or has_site or has_web_verb:
        # Extract the URL or site name as target
        url_match = re.search(r'(https?://[^\s,]+|www\.[^\s,]+)', text)
        if url_match:
            target = url_match.group(0).rstrip(".,;")
        else:
            # Try to grab a full domain like "myntra.com" or "amazon.in"
            domain_match = re.search(r'\b(\w+\.(?:com|org|net|io|in|co\.in|edu|gov|co|me|app))\b', lower)
            if domain_match:
                target = domain_match.group(1)
            else:
                # Extract site name from "go to X" / "open X"  
                site_match = re.search(r'(?:go to|navigate to|open|visit|browse to|log ?in to|search on)\s+(\w+)', lower)
                target = site_match.group(1) if site_match else lower.split()[1] if len(lower.split()) > 1 else text
        
        print(f"DEBUG NLU: PRE-LLM WEB INTERCEPT → WEB_CONTROL target='{target}', context='{text}'")
        return [Command(action="WEB_CONTROL", target=target, context=text)]
    
    # ===== 1. Fast Path (simple single-verb commands) =====
    complex_triggers = ["extract", "calculate", "analyze", "it", "them", "that", "those", "previous", "last"]
    is_complex = len(text.split()) > 4 or any(t in lower for t in complex_triggers)
    
    if not is_complex:
        commands = fast_path_extract(text)
        if commands:
            print(f"DEBUG NLU: Fast Path Success: {commands}")
            return commands
        
    # ===== 2. Fallback to LLM =====
    return extract_commands(text, chat_history=chat_history)
