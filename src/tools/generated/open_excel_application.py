"""
Auto-generated tool: open_excel_application
Do not edit manually.
"""

import os
import subprocess

def execute(params: dict) -> str:
    try:
        excel_path = None
        for root, dirs, files in os.walk("C:\\Program Files\\Microsoft Office\\"):
            if "EXCEL.EXE" in files:
                excel_path = os.path.join(root, "EXCEL.EXE")
                break
        if excel_path is None:
            for root, dirs, files in os.walk("C:\\Program Files (x86)\\Microsoft Office\\"):
                if "EXCEL.EXE" in files:
                    excel_path = os.path.join(root, "EXCEL.EXE")
                    break
        if excel_path is None:
            return "[Error] Excel application not found"
        subprocess.Popen(excel_path)
        return "[Success] Excel application opened"
    except Exception as e:
        return f"[Error] {str(e)}"