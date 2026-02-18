"""
Auto-generated tool: compress_file_to_zip
"""

import os
import zipfile
import sys
from typing import Dict

def _create_zip(file_path: str, zip_path: str, level: int) -> None:
    # Try to use compresslevel if supported (Python 3.7+)
    try:
        with zipfile.ZipFile(zip_path, mode='w',
                             compression=zipfile.ZIP_DEFLATED,
                             compresslevel=level) as zf:
            zf.write(file_path, arcname=os.path.basename(file_path))
    except TypeError:
        # compresslevel not supported; fall back
        with zipfile.ZipFile(zip_path, mode='w',
                             compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(file_path, arcname=os.path.basename(file_path))

def execute(params: Dict) -> str:
    try:
        if 'file_path' not in params:
            return "[Error] 'file_path' parameter is required."

        file_path = params['file_path']
        if not isinstance(file_path, str) or not file_path:
            return "[Error] Invalid 'file_path' value."

        if not os.path.isfile(file_path):
            return f"[Error] File not found: {file_path}"

        zip_path = params.get('zip_path')
        if zip_path:
            if not isinstance(zip_path, str) or not zip_path:
                return "[Error] Invalid 'zip_path' value."
        else:
            base, _ = os.path.splitext(file_path)
            zip_path = f"{base}.zip"

        level = params.get('compression_level', 6)
        if not isinstance(level, int) or not (0 <= level <= 9):
            level = 6  # fallback to default if out of range

        # Ensure destination directory exists
        dest_dir = os.path.dirname(zip_path)
        if dest_dir and not os.path.isdir(dest_dir):
            os.makedirs(dest_dir, exist_ok=True)

        _create_zip(file_path, zip_path, level)
        return f"[Success] Created zip archive at {zip_path}"
    except Exception as e:
        return f"[Error] {str(e)}"