import dspy
from typing import List, Optional
from pydantic import BaseModel, Field

# 1. Define Structured Output
class Command(BaseModel):
    action: str = Field(description="The action to perform: 'OPEN', 'CLOSE', 'TYPE', 'RENAME', 'MOVE', 'SEARCH', 'EXCEL_READ', 'EXCEL_WRITE', 'EXCEL_ADD_ROW', 'EXCEL_DELETE_ROW', 'EXCEL_STYLE', 'SET', 'DYNAMIC_CODE'.")
    target: str = Field(description="The primary object of the action (app name, file name, text to type).")
    context: Optional[str] = Field(None, description="Context. For DYNAMIC_CODE, this is the raw task description.")

class CommandList(BaseModel):
    commands: List[Command]

# 2. Define DSPy Signature
class IntentExtraction(dspy.Signature):
    """
    Extract a list of executable commands from the user's natural language input.
    Split compound sentences (e.g., 'open x and close y') into separate commands.
    Infer the correct action based on context (e.g., 'back the file' -> OPEN/SEARCH).
    """
    user_input: str = dspy.InputField(desc="User's raw command")
    extracted_commands: CommandList = dspy.OutputField(desc="List of structured commands. JSON ONLY.")

# 3. Predictor
class SimpleIntent(dspy.Signature):
    """
    Extract a list of executable commands.
    Output MUST be a JSON object with a distinct key 'commands' containing a LIST of objects.
    
    CRITICAL RULES:
    1. Do NOT nest commands. Return a flat list.
    2. Do NOT use keys like 'action_sequence' or 'next_step'.
    3. Split 'copy text and paste it' into two separate commands.
    4. Use specific keys: 'action', 'target', 'context'.
    
    ACTIONS:
    - OPEN, CLOSE, TYPE, SEARCH, MOVE, RENAME
    - EXCEL_READ, EXCEL_WRITE, EXCEL_ADD_ROW, EXCEL_DELETE_ROW, EXCEL_STYLE
    - DYNAMIC_CODE: Use this for complex, ad-hoc, or multi-step analysis tasks that require custom logic (e.g., "Add 10 dummy rows", "Find max salary", "Sort by date", "Calculate average").
    
    Example Excel Simple:
    User: "Add row to sheet.xlsx with data 10, 20, 30"
    JSON: { "commands": [ {"action": "EXCEL_ADD_ROW", "target": "sheet.xlsx", "context": "10, 20, 30"} ] }

    Example Dynamic:
    User: "Generate 50 random users in sample.xlsx"
    JSON: { "commands": [ {"action": "DYNAMIC_CODE", "target": "sample.xlsx", "context": "Generate 50 random users"} ] }
    """
    user_input: str = dspy.InputField(desc="User's raw command")
    json_output: str = dspy.OutputField(desc="JSON string of commands")

predictor = dspy.Predict(SimpleIntent)

def extract_commands(text: str) -> List[Command]:
    """
    Uses LLM to parse natural language into structured commands.
    """
    import json
    try:
        # 1. Clean input
        clean_text = text.strip()
        
        # 2. Invoke DSPy
        prediction = predictor(user_input=clean_text)
        raw_json = prediction.json_output
        
        # 3. Clean Markdown
        if "```json" in raw_json:
            raw_json = raw_json.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_json:
            raw_json = raw_json.split("```")[1].split("```")[0].strip()
            
        # 4. Parse JSON
        import ast
        try:
            data = json.loads(raw_json)
        except:
            try:
                # Fallback
                data = ast.literal_eval(raw_json)
            except:
                print(f"Failed to parse NLU output: {raw_json}")
                return []
        
        # 5. Recursive Search for Commands
        def find_command_dicts(obj):
            results = []
            if isinstance(obj, list):
                for item in obj:
                    results.extend(find_command_dicts(item))
            elif isinstance(obj, dict):
                # Check if this dict itself is a command
                action_k = obj.get("action") or obj.get("command") or obj.get("action_type")
                is_valid_command = False
                
                if action_k and isinstance(action_k, str):
                    act = action_k.lower()
                    # Filter out wrapper actions like "execute_commands"
                    if "execute" not in act and "sequence" not in act:
                        is_valid_command = True
                
                if is_valid_command:
                    results.append(obj)
                
                # RECURSE into values to find nested commands (e.g. action_sequence, next_step)
                for k, v in obj.items():
                    if isinstance(v, (dict, list)):
                        # If the key suggests a list of commands, prioritize scanning it
                        results.extend(find_command_dicts(v))
            return results

        raw_list = find_command_dicts(data)
        
        # 6. Convert to Pydantic models with Action-Aware mapping
        commands = []
        
        # Helper to process a single dict item
        def process_item(item):
            # 1. Determine Action first
            raw_action = item.get("action") or item.get("command") or item.get("action_type") or "OPEN"
            action_norm = raw_action.upper()
            
            # Normalize common variations
            if "OPEN" in action_norm or "PLAY" in action_norm or "START" in action_norm or "LAUNCH" in action_norm:
                action_norm = "OPEN"
            elif "TYPE" in action_norm or "WRITE" in action_norm:
                action_norm = "TYPE"
            elif "CLOSE" in action_norm or "STOP" in action_norm or "EXIT" in action_norm:
                action_norm = "CLOSE"
            elif "SEARCH" in action_norm or "FIND" in action_norm:
                action_norm = "SEARCH"
            elif "ROW" in action_norm or "DATA" in action_norm:
                if "ADD" in action_norm or "APPEND" in action_norm or "INSERT" in action_norm: action_norm = "EXCEL_ADD_ROW"
                elif "DELETE" in action_norm or "REMOVE" in action_norm: action_norm = "EXCEL_DELETE_ROW"
                # If just "DATA", check context
                elif action_norm == "DATA" and ("sheet" in str(item).lower() or "excel" in str(item).lower()):
                     action_norm = "EXCEL_READ"
            elif "STYLE" in action_norm or "COLOR" in action_norm or "FORMAT" in action_norm:
                action_norm = "EXCEL_STYLE"
            elif "CELL" in action_norm or "WRITE" in action_norm: 
                 if "CELL" in action_norm or "sheet" in str(item).lower():
                     action_norm = "EXCEL_WRITE"
            elif "SET" in action_norm or "UPDATE" in action_norm or "CHANGE" in action_norm or "MODIFY" in action_norm or "CALCULATE" in action_norm or "GENERATE" in action_norm or "ANALYZE" in action_norm or "LIST" in action_norm:
                 # Complex Logic Heuristic
                 ctx_str = str(item.get("context") or "") + str(item.get("target") or "")
                 
                 # Dynamic Routing
                 if "xls" in ctx_str.lower() or "sheet" in ctx_str.lower() or "csv" in ctx_str.lower():
                      if "row" in ctx_str.lower() and "add" in action_norm.lower():
                            action_norm = "EXCEL_ADD_ROW"
                      elif any(k in str(item).lower() for k in ["generate", "dummy", "random", "calculate", "average", "monitor", "highest", "lowest", "sort", "where", "filter", "from", "list"]):
                            # "List from" implies query -> Dynamic
                            action_norm = "DYNAMIC_CODE"
                      else:
                            action_norm = "EXCEL_WRITE"
                 else:
                      if "calculate" in action_norm.lower() or "generate" in action_norm.lower():
                            action_norm = "DYNAMIC_CODE"
            elif "DYNAMIC" in action_norm:
                 action_norm = "DYNAMIC_CODE"
            elif "READ" in action_norm or "DATA" in action_norm:
                 if "sheet" in str(item).lower() or "excel" in str(item).lower():
                     action_norm = "EXCEL_READ"
            elif "EXECUTE" in action_norm:
                 # Check if it is a wrapper for 'action_after...' logic
                 pass
            
            else:
                 # CATCH-ALL: If action is unknown (e.g., "LIST", "FILTER", "EXTRACT")
                 # and target looks like a file, assume DYNAMIC_CODE.
                 ctx_str = str(item.get("context") or "") + str(item.get("target") or "")
                 if any(ext in ctx_str.lower() for ext in ['.xls', '.xlsx', '.csv', 'sheet']):
                      action_norm = "DYNAMIC_CODE"

            # 2. Determine Target based on Action
            target = ""
            context = item.get("context") or item.get("media_language") or item.get("language") or item.get("data") or item.get("values") or item.get("row_content") or item.get("new_data")
            
            # Helper for list/dict context
            if isinstance(context, list):
                context = ", ".join([str(c) for c in context])
            elif isinstance(context, dict):
                # Extract values from dict
                context = ", ".join([str(v) for v in context.values()])

            if action_norm == "TYPE":
                # For TYPE, text is the priority
                target = item.get("text") or item.get("value") or item.get("typed_text") or item.get("string") or item.get("parameter") or item.get("text_to_type")
                if not target:
                    target = item.get("target") or item.get("object") or ""
                if not context:
                    context = item.get("application_name") or item.get("app_name")
            else:
                target = (
                    item.get("application_name") or 
                    item.get("app_name") or
                    item.get("media_title") or 
                    item.get("title") or
                    item.get("file_name") or
                    item.get("filename") or
                    item.get("file") or
                    item.get("target") or
                    item.get("object") or
                    item.get("parameter") or
                    ""
                )
            
            # Add the primary command
            commands.append(Command(action=action_norm, target=target, context=context))
            
            # 3. Check for implicit secondary actions (LLM bad habits)
            # Pattern: "action_after_open": "type_text", "text_to_type": "hi"
            next_action = item.get("action_after_open") or item.get("next_action")
            if next_action:
                # Recursively process this as a new item using the SAME dict 
                # but overriding the action and looking for specific keys
                # Simplify: just construct a new dict
                new_item = item.copy()
                new_item["action"] = next_action
                # Remove the trigger to avoid infinite loop
                new_item.pop("action_after_open", None) 
                new_item.pop("next_action", None)
                
                # If specific keys exist for the next action, ensure they are picked up
                # e.g. text_to_type -> text
                if "text_to_type" in item:
                    new_item["text"] = item["text_to_type"]
                
                process_item(new_item)

        for item in raw_list:
             process_item(item)
            
        if not commands and clean_text:
             # FALLBACK: If NLU failed to structure it, force DYNAMIC_CODE.
             # This fulfills the "Self Adoptive" requirement.
             print(f"NLU Fallback: forcing DYNAMIC_CODE for '{clean_text}'")
             commands.append(Command(action="DYNAMIC_CODE", target="active_workbook", context=clean_text))

        return commands
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        # Even on error, try fallback? No, simpler to just return single fallback if possible.
        print(f"NLU Error: {e}")
        return [Command(action="DYNAMIC_CODE", target="active_workbook", context=text)]
