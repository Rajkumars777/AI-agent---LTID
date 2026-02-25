"""
Cached S1-Grade code for: Create a folder named 'Invoices' on the desktop
Generated: 2026-02-25 09:28
"""

def execute(params: dict) -> str:
    try:
        folder_name = "Invoices"
        desktop_path = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')

        # Create folder
        folder_path = os.path.join(desktop_path, folder_name)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        return f"[Success] Folder '{folder_name}' created on desktop"
    except Exception as e:
        return f"[Error] {str(e)}"