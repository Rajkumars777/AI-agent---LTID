"""
Auto-generated tool: compress_excel_to_zip
"""

def execute(params: dict) -> str:
    import os
    import zipfile

    # Validate required parameters
    required_keys = {"source_path", "zip_path"}
    missing = required_keys - params.keys()
    if missing:
        return f"[Error] Missing parameters: {', '.join(missing)}"

    source_path = params["source_path"]
    zip_path = params["zip_path"]

    # Check if source file exists
    if not os.path.isfile(source_path):
        return f"[Error] Source file does not exist: {source_path}"

    # Ensure the directory for the zip file exists
    zip_dir = os.path.dirname(zip_path) or "."
    if not os.path.isdir(zip_dir):
        try:
            os.makedirs(zip_dir, exist_ok=True)
        except Exception as e:
            return f"[Error] Could not create directory for zip file: {e}"

    try:
        with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            # Add the source file to the zip archive with its basename
            zf.write(source_path, arcname=os.path.basename(source_path))
    except Exception as e:
        return f"[Error] Failed to create zip: {e}"

    return f"[Success] Created zip archive at {zip_path}"