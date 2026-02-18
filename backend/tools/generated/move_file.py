"""
Auto-generated tool: move_file
Do not edit manually.
"""

import os
import shutil
from pathlib import Path

def execute(params: dict) -> str:
    try:
        source_path = params.get("source_path", "").strip()
        destination_dir = params.get("destination_path", "").strip()

        if not source_path:
            raise ValueError("Parameter 'source_path' is required.")
        if not destination_dir:
            raise ValueError("Parameter 'destination_path' is required.")

        src = Path(source_path)
        dst_dir = Path(destination_dir)

        if not src.exists():
            raise FileNotFoundError(f"Source path does not exist: {src}")

        # Ensure destination directory exists
        dst_dir.mkdir(parents=True, exist_ok=True)

        # Destination file path (preserve original name)
        dst = dst_dir / src.name

        # Perform move
        shutil.move(str(src), str(dst))

        return f"[Success] Moved '{src}' to '{dst}'."
    except Exception as e:
        return f"[Error] {str(e)}"