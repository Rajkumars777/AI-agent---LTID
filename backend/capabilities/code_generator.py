import dspy
import os
import sys
import io
import pandas as pd
import openpyxl
import traceback
import tempfile

class ScriptGenerator(dspy.Signature):
    """
    You are a Python Expert. Write a Python script to perform the user's task.
    
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
    
    DATA RETRIEVAL GUIDELINES (for tasks involving fetching data from the internet):
    12. **STOCK DATA**: Use `yfinance` library to fetch stock/index data.
        - Example: `import yfinance as yf; data = yf.download("^N225", period="10d")`
        - Common tickers: ^N225 (Nikkei), ^GSPC (S&P 500), ^DJI (Dow Jones), ^IXIC (NASDAQ),
          ^BSESN (BSE Sensex), ^NSEI (Nifty 50), AAPL, GOOGL, MSFT, TSLA, etc.
    13. **WEB DATA**: Use `requests` + `beautifulsoup4` for web scraping.
        - Example: `import requests; from bs4 import BeautifulSoup; resp = requests.get(url); soup = BeautifulSoup(resp.text, 'html.parser')`
    14. **ROUNDING**: When asked to round values, use `.round(2)` on DataFrame columns.
    15. **DATE FORMATTING**: Format dates as strings: `df['Date'] = df.index.strftime('%Y-%m-%d')` for datetime indices.
    16. **COMBINED TASKS**: If task involves BOTH data retrieval AND file creation:
        - Fetch the data first
        - Process/clean/round it
        - Create DataFrame
        - Save to Excel
        - Print summary as HTML
    """
    task = dspy.InputField(desc="The natural language task description")
    file_path = dspy.InputField(desc="The absolute path to the file to operate on (may be 'auto' for new files)")
    python_code = dspy.OutputField(desc="The executable Python script")

# Initialize Predictor
generator = dspy.Predict(ScriptGenerator)

def generate_and_run_script(task: str, file_path: str) -> str:
    """
    Generates a script for the task and executes it.
    Supports: Excel ops, data retrieval (yfinance, requests), file creation.
    """
    print(f"DEBUG: Generating script for: {task} on {file_path}")
    
    # 0. Context Enhancement: Read Structure or Note File Missing
    structure_info = ""
    file_exists = os.path.exists(file_path)
    
    if file_exists:
        try:
            if file_path.endswith(('.csv', '.xls', '.xlsx')):
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
        
        # If still not found and user wants to create
        if not file_exists:
            # Check if this is a data retrieval + file creation task
            task_lower = task.lower()
            is_data_task = any(kw in task_lower for kw in [
                "stock", "price", "retrieve", "fetch", "download", "scrape",
                "nikkei", "sensex", "nifty", "s&p", "dow", "nasdaq",
                "closing", "opening", "market", "exchange rate", "currency",
                "gold price", "silver price", "crypto", "bitcoin"
            ])
            
            if is_data_task:
                structure_info = """
NOTE: This is a DATA RETRIEVAL + FILE CREATION task. You must:
1. Use yfinance or requests to fetch the data
2. Process and clean the data (round to 2 decimal places if requested)
3. Create a DataFrame with the data
4. import tempfile, os
5. Save to: temp_path = os.path.join(tempfile.gettempdir(), 'retrieved_data.xlsx')
6. df.to_excel(temp_path, index=False)
7. os.startfile(temp_path)
8. print(df.to_html(classes='generated-table', index=False))
9. print("Data saved and opened in Excel!")
"""
            elif "add" in task_lower or "create" in task_lower or "generate" in task_lower:
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
        # 1. Generate Code — try DSPy Predict first, fallback to direct LLM call
        code = None
        
        try:
            prediction = generator(task=final_task, file_path=file_path)
            code = prediction.python_code
            print(f"DEBUG CodeGen: DSPy Predict returned code length={len(code) if code else 0}", flush=True)
        except Exception as pred_err:
            print(f"DEBUG CodeGen: DSPy Predict failed: {pred_err}", flush=True)
        
        # Fallback: Direct LLM call if DSPy returned empty
        if not code or len(code.strip()) < 10:
            print("DEBUG CodeGen: Falling back to direct LLM call...", flush=True)
            direct_prompt = f"""Write a complete Python script for this task:

TASK: {final_task}

FILE PATH: {file_path}

RULES:
- Output ONLY valid Python code, no markdown, no explanation
- Include all imports at the top
- Use yfinance for stock data (e.g., yf.download("^N225", period="15d"))
- Use pandas for DataFrames
- Use os.path.join(tempfile.gettempdir(), 'data.xlsx') for output path
- Round numeric values to 2 decimal places when requested
- At the end: save to Excel, open with os.startfile(), print the DataFrame as HTML

Python code:"""
            try:
                resp = dspy.settings.lm(direct_prompt)
                if isinstance(resp, list):
                    code = resp[0] if resp else ""
                else:
                    code = str(resp)
                print(f"DEBUG CodeGen: Direct LLM returned code length={len(code) if code else 0}", flush=True)
            except Exception as lm_err:
                print(f"DEBUG CodeGen: Direct LLM also failed: {lm_err}", flush=True)
                return f"Error: LLM failed to generate code. DSPy error + direct call error.\nDirect error: {lm_err}"
        
        if not code or len(code.strip()) < 10:
            return "Error: LLM failed to generate code (empty response from both DSPy and direct call)."

        # Clean Markdown if present
        if "```" in code:
            code = code.replace("```python", "").replace("```", "").strip()
            
        # Clean potential wrapped quotes
        code = code.strip().strip('"').strip("'")
        
        # 1.5 Safety Validation (AST Analysis)
        from capabilities.safety_engine import validate_code
        is_safe, safety_msg = validate_code(code)
        if not is_safe:
            print(f"BLOCKING UNSAFE CODE: {safety_msg}")
            return f"❌ **Safety Block:** The generated script was blocked for security reasons.\n**Reason:** {safety_msg}\n\n**Blocked Script:**\n```python\n{code}\n```"

        # FIX: Unescape literal newlines if LLM returned a string representation
        code = code.replace('\\n', '\n')
        
        print(f"DEBUG: Generated Code:\n{code}")
        
        # 2. Execution Environment
        output_buffer = io.StringIO()
        
        # Build execution globals with all available libraries
        execution_globals = {
            "pd": pd,
            "openpyxl": openpyxl,
            "os": os,
            "sys": sys,
            "tempfile": tempfile,
            "io": io,
            "print": lambda *args, **kwargs: print(*args, file=output_buffer, **kwargs),
        }
        
        # Add optional data retrieval libraries
        try:
            import yfinance
            execution_globals["yfinance"] = yfinance
            execution_globals["yf"] = yfinance
        except ImportError:
            print("Warning: yfinance not installed. Stock data retrieval may fail.")
            
        try:
            import requests
            execution_globals["requests"] = requests
        except ImportError:
            print("Warning: requests not installed.")
            
        try:
            from bs4 import BeautifulSoup
            execution_globals["BeautifulSoup"] = BeautifulSoup
        except ImportError:
            pass

        try:
            import numpy as np
            execution_globals["np"] = np
        except ImportError:
            pass
        
        try:
            from datetime import datetime, timedelta
            execution_globals["datetime"] = datetime
            execution_globals["timedelta"] = timedelta
        except ImportError:
            pass
        
        # 3. Execute
        try:
            exec(code, execution_globals)
            
            output = output_buffer.getvalue()
            if not output:
                output = "Script executed successfully (No output)."
                
            return f"**Generated & Executed Script:**\n```python\n{code}\n```\n\n**Output:**\n{output}"
            
        except Exception as exec_err:
            error_msg = traceback.format_exc()
            
            # SELF-HEALING: Try once more with error context
            print(f"First attempt failed, trying self-heal...")
            try:
                heal_task = f"{final_task}\n\nPREVIOUS CODE FAILED WITH ERROR:\n{error_msg}\n\nFix the code to handle this error."
                prediction2 = generator(task=heal_task, file_path=file_path)
                code2 = prediction2.python_code
                if code2:
                    if "```" in code2:
                        code2 = code2.replace("```python", "").replace("```", "").strip()
                    code2 = code2.strip().strip('"').strip("'").replace('\\n', '\n')
                    
                    output_buffer2 = io.StringIO()
                    execution_globals["print"] = lambda *args, **kwargs: print(*args, file=output_buffer2, **kwargs)
                    exec(code2, execution_globals)
                    output2 = output_buffer2.getvalue()
                    if not output2:
                        output2 = "Script executed successfully (No output)."
                    return f"**Generated & Executed Script (self-healed):**\n```python\n{code2}\n```\n\n**Output:**\n{output2}"
            except Exception as heal_err:
                pass
            
            return f"**Error executing generated script:**\n```python\n{code}\n```\n\n**Error:**\n{error_msg}"

    except Exception as gen_err:
        return f"Error generating script: {str(gen_err)}"
