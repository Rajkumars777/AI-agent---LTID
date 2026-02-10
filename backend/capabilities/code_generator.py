import dspy
import os
import sys
import io
import pandas as pd
import openpyxl
import traceback

class ScriptGenerator(dspy.Signature):
    """
    You are a Python Expert. Write a Python script to perform the user's task on the specified file.
    
    GUIDELINES:
    1. Use 'pandas' or 'openpyxl' for Excel/CSV files.
    2. The script must be self-contained (imports included).
    3. **WINDOWS PATHS**: ALWAYS use raw strings for file paths! Use `r'C:\\path\\to\\file'` format.
    4. **CREATE/GENERATE DATA**: When creating new data:
       - Create the DataFrame with the requested data
       - Save to a TEMP file: `import tempfile; temp_path = os.path.join(tempfile.gettempdir(), 'generated_data.xlsx')`
       - Save: `df.to_excel(temp_path, index=False)`
       - Open in Excel: `os.startfile(temp_path)`
       - Print: `print("Opened in Excel! Use File > Save As to save to your preferred location.")`
    5. **MODIFY EXISTING**: If modifying an EXISTING file, save changes back to the file and open it.
    6. **READ/ANALYZE**: For reading/analysis tasks, print as HTML: `print(df.to_html(classes='generated-table', index=False))`
    7. Do NOT use placeholder file paths. Use the exact 'file_path' provided if it exists.
    8. Handle potential errors gracefully.
    9. Output ONLY valid Python code. No markdown blocks. No newlines inside strings.
    10. **XLS FORMAT**: If the input file is `.xls`, READ it using `pd.read_excel`. Save to `.xlsx`.
    11. **FIELD MAPPING**: Map natural language column names to actual column names.
    """
    task = dspy.InputField(desc="The natural language task description (e.g., 'add 10 dummy rows', 'find highest salary')")
    file_path = dspy.InputField(desc="The absolute path to the file to operate on")
    python_code = dspy.OutputField(desc="The executable Python script")

# Initialize Predictor
generator = dspy.Predict(ScriptGenerator)

def generate_and_run_script(task: str, file_path: str) -> str:
    """
    Generates a script for the task and executes it.
    """
    print(f"DEBUG: Generating script for: {task} on {file_path}")
    
    # 0. Context Enhancement: Read Structure or Note File Missing
    structure_info = ""
    file_exists = os.path.exists(file_path)
    
    if file_exists:
        try:
            if file_path.endswith(('.csv', '.xls', '.xlsx')):
                # Read just header
                if file_path.endswith('.csv'):
                    df_header = pd.read_csv(file_path, nrows=0)
                else:
                    df_header = pd.read_excel(file_path, nrows=0)
                
                columns = list(df_header.columns)
                structure_info = f"\nThe file exists and has the following columns: {columns}. Use these EXACT names."
        except Exception as e:
            print(f"Warning: Could not read structure: {e}")
            structure_info = f"\nNote: Could not read file structure: {e}"
    else:
        # File doesn't exist - tell the LLM to CREATE it
        structure_info = f"""
NOTE: The file '{file_path}' does NOT exist yet. You must CREATE it.
For new Excel files:
1. Create a new DataFrame with appropriate columns for the data
2. Save it using df.to_excel(file_path, index=False)
For example, if adding dummy employee data, create columns like: ['Name', 'Age', 'Email', 'Salary']
"""
        # Also try common locations as fallback
        user_home = os.path.expanduser("~")
        common_locations = [
            os.path.join(user_home, "Documents", os.path.basename(file_path)),
            os.path.join(user_home, "Downloads", os.path.basename(file_path)),
            os.path.join(user_home, "Desktop", os.path.basename(file_path)),
        ]
        
        for loc in common_locations:
            if os.path.exists(loc):
                file_path = loc
                file_exists = True
                try:
                    df_header = pd.read_excel(loc, nrows=0)
                    columns = list(df_header.columns)
                    structure_info = f"\nFound file at: {loc}. Columns: {columns}. Use these EXACT names."
                except:
                    pass
                break
        
        
        # If still not found and user wants to create, create temp file and open in Excel
        if not file_exists and ("add" in task.lower() or "create" in task.lower() or "generate" in task.lower()):
            structure_info = """
NOTE: This is a CREATE/GENERATE task. You must:
1. import tempfile, os
2. Create DataFrame with the requested data
3. Save to temp file: temp_path = os.path.join(tempfile.gettempdir(), 'generated_data.xlsx')
4. df.to_excel(temp_path, index=False)
5. os.startfile(temp_path)
6. print('Opened in Excel! Use File > Save As to save.')
"""


    final_task = task + structure_info

    
    try:
        # 1. Generate Code
        prediction = generator(task=final_task, file_path=file_path)
        code = prediction.python_code
        
        if not code:
            return "Error: LLM failed to generate code."

        # Clean Markdown if present
        if "```" in code:
            code = code.replace("```python", "").replace("```", "").strip()
            
        # Clean potential wrapped quotes
        code = code.strip().strip('"').strip("'")
        
        # FIX: Unescape literal newlines if LLM returned a string representation
        # This handles cases where LLM returns "import os\nimport sys" as a string literal
        code = code.replace('\\n', '\n')
        
        print(f"DEBUG: Generated Code:\n{code}")
        
        # 2. Execution Environment
        # Capture stdout to return as result
        output_buffer = io.StringIO()
        
        # Define safe globals/locals
        # We allow standard libs + data libs
        execution_globals = {
            "pd": pd,
            "openpyxl": openpyxl,
            "os": os,
            "print": lambda *args: print(*args, file=output_buffer) # Redirect print
        }
        
        # 3. Execute
        try:
            # We use exec() - Caution: This allows arbitrary code execution. 
            # In a real generic agent, this needs sandboxing (Docker/Wasmer).
            # For this local assistant, we rely on the LLM being helpful.
            exec(code, execution_globals)
            
            output = output_buffer.getvalue()
            if not output:
                output = "Script executed successfully (No output)."
                
            return f"**Generated & Executed Script:**\n```python\n{code}\n```\n\n**Output:**\n{output}"
            
        except Exception as exec_err:
            error_msg = traceback.format_exc()
            return f"**Error executing generated script:**\n```python\n{code}\n```\n\n**Error:**\n{error_msg}"

    except Exception as gen_err:
        return f"Error generating script: {str(gen_err)}"
            return f"**Error executing generated script:**\n```python\n{code}\n```\n\n**Error:**\n{error_msg}"

    except Exception as gen_err:
        return f"Error generating script: {str(gen_err)}"
