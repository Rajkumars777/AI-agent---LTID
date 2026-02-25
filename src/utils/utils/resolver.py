import os
import sys
import glob
from typing import List

def find_file_paths(filename: str) -> List[str]:
    """
    Standalone search for files within the project and common data directories.
    """
    # Prefer current working directory and backend root
    base_dirs = [os.getcwd(), os.path.dirname(os.path.dirname(os.path.abspath(__file__)))]
    
    candidates = []
    for base in base_dirs:
        # Shallow search first for performance
        pattern = os.path.join(base, "**", filename)
        matches = glob.glob(pattern, recursive=True)
        candidates.extend([m for m in matches if os.path.isfile(m)])
    
    # Remove duplicates
    return list(set(candidates))

def resolve_file_arg(filename: str) -> str:
    """
    Takes a filename (e.g., 'report.pdf') and returns the absolute path.
    If multiple exist, returns the most recently modified one.
    """
    if not filename or not isinstance(filename, str):
        return filename

    # 1. If it's already a valid path, return it.
    if os.path.isabs(filename) and os.path.exists(filename):
        return filename
    
    # Check if exists in current directory
    if os.path.exists(filename):
        return os.path.abspath(filename)

    # 2. Search for the file
    print(f"🔍 Resolver: Searching for '{filename}'...")
    candidates = find_file_paths(filename)
    
    if not candidates:
        print(f"⚠️ Resolver: Could not find '{filename}'")
        return filename
    
    # 3. Smart Selection: If multiple files, pick the newest one
    try:
        best_match = max(candidates, key=lambda p: os.path.getmtime(p) if os.path.exists(p) else 0)
        print(f"✅ Resolver Resolved: '{filename}' -> '{best_match}'")
        return best_match
    except Exception as e:
        print(f"⚠️ Resolver selection error: {e}")
        return candidates[0]
