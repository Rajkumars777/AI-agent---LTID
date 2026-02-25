"""
Auto-generated tool: open_pdf_file
Do not edit manually.
"""

import os
import subprocess

def execute(params: dict) -> str:
    try:
        file_name = params.get("file_name", "")
        if not file_name:
            return "[Error] File name is required"
        if not file_name.endswith(".pdf"):
            file_name += ".pdf"
        if not os.path.exists(file_name):
            return f"[Error] File {file_name} not found"
        subprocess.run(f"start {file_name}", shell=True, check=True)
        return "[Success] PDF file opened"
    except Exception as e:
        return f"[Error] {str(e)}"