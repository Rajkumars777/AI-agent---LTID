"""
Auto-generated tool: open_file_tool
Do not edit manually.
"""

import os
import subprocess

def execute(params: dict) -> str:
    try:
        file_path = params.get("file_path", "")
        if not file_path:
            return "[Error] File path is required"
        if not os.path.exists(file_path):
            return "[Error] File does not exist"
        if not os.path.isfile(file_path):
            return "[Error] Path is not a file"
        subprocess.run(f'start "{file_path}"', shell=True, check=True)
        return "[Success] File opened successfully"
    except Exception as e:
        return f"[Error] {str(e)}"