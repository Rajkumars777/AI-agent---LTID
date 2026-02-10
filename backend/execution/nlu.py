import dspy
from typing import List, Optional
from pydantic import BaseModel, Field

# 1. Define Structured Output
class Command(BaseModel):
    action: str = Field(description="The action to perform: 'OPEN', 'CLOSE', 'TYPE', 'RENAME', 'MOVE', 'DELETE', 'SEARCH', 'EXCEL_READ', 'EXCEL_WRITE', 'EXCEL_ADD_ROW', 'EXCEL_DELETE_ROW', 'EXCEL_STYLE', 'EXCEL_REFRESH_PIVOTS', 'SET', 'DYNAMIC_CODE', 'DOC_REPORT'.")
    target: str = Field(description="The primary object of the action (app name, file name, text to type).")
    context: Optional[str] = Field(None, description="Context. For DYNAMIC_CODE, this is the raw task description.")

class CommandList(BaseModel):
    commands: List[Command]

# 2. Define DSPy Signature
class SimpleIntent(dspy.Signature):
    """
    Extract a list of executable commands.
    Output MUST be a JSON object with a distinct key 'commands' containing a LIST of objects.
    
    ACTIONS:
    - OPEN, CLOSE, TYPE, SEARCH, MOVE, RENAME, DELETE
    - EXCEL_READ, EXCEL_WRITE, EXCEL_ADD_ROW, EXCEL_DELETE_ROW, EXCEL_STYLE
    - DYNAMIC_CODE: Use this for complex, ad-hoc, or multi-step analysis tasks that require custom logic (e.g., "Add 10 dummy rows", "Find max salary", "Sort by date", "Calculate average").
    - DOC_REPORT: Use this when the user wants to extract/filter data and save it to a Word document, PDF, or create a report from data.
    
    CRITICAL RULES:
    1. **Compound Commands**: Split "open X and type Y" into multiple commands.
       - Example: "Open notepad and type hello" -> [{"action": "OPEN", "target": "notepad"}, {"action": "TYPE", "target": "hello"}]
    2. **Type in File**: If user says "type X in Y", split it:
       - Example: "Type about AI in notes.txt" -> [{"action": "OPEN", "target": "notes.txt"}, {"action": "TYPE", "target": "about AI"}]
       - Example: "Type hello in notepad" -> [{"action": "OPEN", "target": "notepad"}, {"action": "TYPE", "target": "hello"}]
    3. **Delete**: "delete file", "remove file" -> DELETE
       - Example: "delete sample.xlsx file" -> [{"action": "DELETE", "target": "sample.xlsx"}]
       - Example: "remove notes.txt" -> [{"action": "DELETE", "target": "notes.txt"}]
    4. **Excel**:
       - "add row..." -> EXCEL_ADD_ROW
       - "delete row..." -> EXCEL_DELETE_ROW
       - "style..." -> EXCEL_STYLE
       - "refresh pivots" -> EXCEL_REFRESH_PIVOTS
       - "read sheet..." -> EXCEL_READ
    5. **Dynamic Code**: ONLY use DYNAMIC_CODE if the request requires complex logic, loops, or data generation that cannot be handled by standard tools.
       - "Calculate fibonacci" -> DYNAMIC_CODE
    6. **Search**: "find file", "search for" -> SEARCH
    7. **System**: "minimize", "maximize" -> SET
    8. **Document Reports**: Use DOC_REPORT when the user wants to extract/filter data FROM a file and save/store it INTO a Word document or create a report.
       - "extract employees with salary > 50000 and store in word document" -> DOC_REPORT (target=source file, context=full request)
       - "create a report from sample.xlsx" -> DOC_REPORT
       - "save filtered data to word" -> DOC_REPORT
    """
    user_input: str = dspy.InputField(desc="User's natural language command")
    commands: CommandList = dspy.OutputField(desc="JSON list of commands", format=CommandList)

predictor = dspy.Predict(SimpleIntent)

def extract_commands(text: str) -> List[Command]:
    """
    Uses LLM to parse natural language into structured commands.
    """
    try:
        # 1. Clean input
        clean_text = text.strip()
        print(f"DEBUG NLU: Input text: '{clean_text}'")
        
        # 2. Invoke DSPy
        prediction = predictor(user_input=clean_text)
        print(f"DEBUG NLU: Prediction received: {prediction}")
        
        # 3. Handle Typed Output
        # prediction.commands is a CommandList object
        if hasattr(prediction, 'commands') and hasattr(prediction.commands, 'commands'):
             print(f"DEBUG NLU: Commands extracted: {prediction.commands.commands}")
             return prediction.commands.commands
        
        # Fallback if something weird happens
        print("Warning: NLU did not return CommandList object.")
        print(f"DEBUG NLU: Prediction attributes: {dir(prediction)}")
        return []

    except Exception as e:
        print(f"Error in NLU: {str(e)}")
        import traceback
        traceback.print_exc()
        return []
