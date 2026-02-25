"""
Auto-generated tool: calculate_math_expression
Do not edit manually.
"""

import os
import subprocess

def execute(params: dict) -> str:
    try:
        expression = params.get("expression", "")
        if not expression:
            return "[Error] No mathematical expression provided"
        
        # Use the built-in Windows Calculator to evaluate the expression
        calc_process = subprocess.Popen(f'calc {expression}', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = calc_process.communicate()
        
        if calc_process.returncode != 0:
            return f"[Error] Failed to evaluate expression: {error.decode('utf-8')}"
        
        # Since the output is not directly available from the calc command, 
        # we will use a workaround by using the 'expr' command in Windows
        # which is available in the Windows Command Prompt
        expr_process = subprocess.Popen(f'expr {expression}', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = expr_process.communicate()
        
        if expr_process.returncode != 0:
            return f"[Error] Failed to evaluate expression: {error.decode('utf-8')}"
        
        result = output.decode('utf-8').strip()
        return f"[Success] The result of the expression '{expression}' is: {result}"
    except Exception as e:
        return f"[Error] {str(e)}"