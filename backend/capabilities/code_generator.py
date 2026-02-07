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
    3. If the task is to MODIFY data: Save the file in-place. Print "File updated successfully."
    4. If the task is to READ/ANALYZE/LIST data: DO NOT print raw lists or dicts. Convert the result to a pandas DataFrame and print `print(df.to_html(classes='generated-table', index=False))`. This is CRITICAL for user UI.
    5. Do NOT use placeholder file paths. Use the exact 'file_path' provided.
    6. Handle potential errors gracefully.
    7. Output ONLY valid Python code. No markdown blocks.
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
    
    # 0. Context Enhancement: Read Structure
    structure_info = ""
    try:
        if file_path.endswith(('.csv', '.xls', '.xlsx')):
            # Read just header
            if file_path.endswith('.csv'):
                df_header = pd.read_csv(file_path, nrows=0)
            else:
                df_header = pd.read_excel(file_path, nrows=0)
            
            columns = list(df_header.columns)
            structure_info = f"\nThe file has the following columns: {columns}. Use these EXACT names."
    except Exception as e:
        print(f"Warning: Could not read structure: {e}")

    final_task = task + structure_info
    
    try:
        # 1. Generate Code
        prediction = generator(task=final_task, file_path=file_path)
        code = prediction.python_code
        
        # Clean Markdown if present
        if "```" in code:
            code = code.replace("```python", "").replace("```", "").strip()
            
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
