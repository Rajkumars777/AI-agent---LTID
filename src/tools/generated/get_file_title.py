"""
Auto-generated tool: get_file_title
Do not edit manually.
"""

import os
import ctypes

def execute(params: dict) -> str:
    try:
        file_path = params.get("file_path", "")
        if not file_path:
            return "[Error] File path is required"
        
        if not os.path.exists(file_path):
            return "[Error] File does not exist"
        
        file_name = os.path.basename(file_path)
        title = os.path.splitext(file_name)[0]
        return f"[Success] {title}"
    except Exception as e:
        return f"[Error] {str(e)}"