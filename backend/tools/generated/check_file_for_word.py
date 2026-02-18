"""
Auto-generated tool: check_file_for_word
Do not edit manually.
"""

import os
from pathlib import Path

def execute(params: dict) -> str:
    try:
        file_path = params.get("file_path", "")
        search_term = params.get("search_term", "")
        if not file_path:
            raise ValueError("Missing 'file_path' parameter.")
        if not search_term:
            raise ValueError("Missing 'search_term' parameter.")
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")
        # Read file content as text, ignoring decode errors
        content = path.read_text(encoding="utf-8", errors="ignore")
        if search_term in content:
            return f"[Success] The term '{search_term}' was found in '{file_path}'."
        else:
            return f"[Success] The term '{search_term}' was NOT found in '{file_path}'."
    except Exception as e:
        return f"[Error] {str(e)}"