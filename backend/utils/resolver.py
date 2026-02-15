import os
import sys
from typing import List

# Ensure we can import from capabilities
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from capabilities.desktop import find_file_paths

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

    # 2. Search for the file (Using cached/smart search)
    print(f"🔍 Resolver: Searching for '{filename}'...")
    candidates = find_file_paths(filename)
    
    if not candidates:
        print(f"⚠️ Resolver: Could not find '{filename}'")
        return filename # Fallback to original string, handler might handle it

    # 3. Smart Selection: If multiple files, pick the newest one
    # This solves the "Context" issue where user likely means the file they just created/downloaded.
    try:
        best_match = max(candidates, key=lambda p: os.path.getmtime(p) if os.path.exists(p) else 0)
        print(f"✅ Resolver Resolved: '{filename}' -> '{best_match}'")
        return best_match
    except Exception as e:
        print(f"⚠️ Resolver selection error: {e}")
        return candidates[0]
