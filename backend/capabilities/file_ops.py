import os
import shutil
from typing import List, Dict

def list_files(directory: str) -> List[str]:
    """List all files in a directory."""
    try:
        return os.listdir(directory)
    except FileNotFoundError:
        return [f"Error: Directory {directory} not found."]

def move_file(source: str, destination: str) -> str:
    """Move a file from source to destination."""
    try:
        shutil.move(source, destination)
        return f"Successfully moved {source} to {destination}"
    except Exception as e:
        return f"Error moving file: {str(e)}"

def rename_file(old_name: str, new_name: str) -> str:
    """Rename a file."""
    try:
        os.rename(old_name, new_name)
        return f"Successfully renamed {old_name} to {new_name}"
    except Exception as e:
        return f"Error renaming file: {str(e)}"

def read_file(file_path: str) -> str:
    """Read content of a text file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"
