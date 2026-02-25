"""
Auto-generated tool: check_file_exists
Do not edit manually.
"""

import os

def execute(params: dict) -> str:
    try:
        filename = params.get("filename", "")
        if os.path.isfile(filename):
            return f"[Success] File {filename} exists in the current directory"
        else:
            return f"[Success] File {filename} does not exist in the current directory"
    except Exception as e:
        return f"[Error] {str(e)}"