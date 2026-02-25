"""
Auto-generated tool: get_document_title
Do not edit manually.
"""

import os
import subprocess

def execute(params: dict) -> str:
    try:
        file_name = params.get("file_name", "")
        if not file_name:
            return "[Error] File name is required"
        
        if not os.path.exists(file_name):
            return f"[Error] File {file_name} does not exist"
        
        if file_name.endswith(".pdf"):
            command = f'pdftotext -f 1 -l 1 "{file_name}" -'
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            output, error = process.communicate()
            if process.returncode != 0:
                return f"[Error] Failed to extract title from {file_name}: {error.decode('utf-8')}"
            title = output.decode('utf-8').strip()
            return f"[Success] Title: {title}"
        elif file_name.endswith(('.docx', '.doc')):
            command = f'antiword "{file_name}"'
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            output, error = process.communicate()
            if process.returncode != 0:
                return f"[Error] Failed to extract title from {file_name}: {error.decode('utf-8')}"
            lines = output.decode('utf-8').splitlines()
            title = lines[0].strip() if lines else ''
            return f"[Success] Title: {title}"
        else:
            return f"[Error] Unsupported file format: {file_name}"
    except Exception as e:
        return f"[Error] {str(e)}"