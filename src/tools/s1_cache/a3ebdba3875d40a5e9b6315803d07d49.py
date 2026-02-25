"""
Cached S1-Grade code for: List all files in the downloads
Generated: 2026-02-25 09:39
"""

import os

def execute(params: dict) -> str:
    try:
        # 1. Open File Explorer
        desktop.open_application("File Explorer")
        if not wait_for_window("File Explorer", timeout=15):
            return "[Error] File Explorer did not open"
        time.sleep(0.8)

        # 2. Navigate to Downloads
        pyautogui.hotkey("ctrl", "l")
        time.sleep(0.3)
        pyperclip.copy(os.path.join(os.path.expanduser("~"), "Downloads"))
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.2)
        pyautogui.press("enter")
        time.sleep(2.0)   # wait for Downloads to load

        # 3. List files in Downloads
        files = os.listdir(os.path.join(os.path.expanduser("~"), "Downloads"))
        file_list = "\n".join(files)

        return f"[Success] Files in Downloads:\n{file_list}"
    except Exception as e:
        return f"[Error] {str(e)}"