"""
Auto-generated tool: move_file_to_folder
Do not edit manually.
"""

import os
import shutil

def execute(params: dict) -> str:
    try:
        file_name = params.get("file_name", "")
        destination_folder = params.get("destination_folder", "")
        
        if not file_name or not destination_folder:
            return "[Error] File name and destination folder are required"
        
        if not os.path.exists(file_name):
            return f"[Error] File {file_name} does not exist"
        
        if not os.path.exists(destination_folder):
            return f"[Error] Destination folder {destination_folder} does not exist"
        
        shutil.move(file_name, destination_folder)
        return f"[Success] File {file_name} moved to {destination_folder}"
    except Exception as e:
        return f"[Error] {str(e)}"