"""
Auto-generated tool: rename_file
Do not edit manually.
"""

import os
import shutil
from pathlib import Path

def execute(params: dict) -> str:
    try:
        source_path = params.get("source_path", "")
        new_path = params.get("new_path", "")

        if not source_path:
            raise ValueError("Parameter 'source_path' is required.")
        if not new_path:
            raise ValueError("Parameter 'new_path' is required.")

        src = Path(source_path).expanduser().resolve()
        dst = Path(new_path).expanduser().resolve()

        if not src.is_file():
            raise FileNotFoundError(f"Source file does not exist: {src}")

        # Ensure destination directory exists
        dst_parent = dst.parent
        if not dst_parent.exists():
            dst_parent.mkdir(parents=True, exist_ok=True)

        # Perform rename/move
        shutil.move(str(src), str(dst))

        return f"[Success] Renamed '{src}' to '{dst}'"
    except Exception as e:
        return f"[Error] {str(e)}"