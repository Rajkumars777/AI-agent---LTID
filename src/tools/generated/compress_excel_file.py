"""
Auto-generated tool: compress_excel_file
"""

import zipfile
import os

def execute(params: dict) -> str:
    file_path = params.get("file_path")
    if not file_path:
        return "[Error] File path is required."

    try:
        # Create a ZipFile object
        with zipfile.ZipFile(file_path + '.zip', 'w') as zip_file:
            # Write the Excel file to the zip
            zip_file.write(file_path)
        return f"[Success] {file_path} has been compressed into a zip."
    except Exception as e:
        return f"[Error] An error occurred: {str(e)}"