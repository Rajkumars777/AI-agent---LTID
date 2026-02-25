"""
Cached S1-Grade code for: Move mohan_eaadhar.pdf to the documents folder
Generated: 2026-02-25 09:30
"""

def execute(params: dict) -> str:
    try:
        file_name = "mohan_eaadhar.pdf"
        destination_folder = params.get("destination_folder", "Documents")

        # 1. Open File Explorer
        desktop.open_application("File Explorer")
        if not wait_for_window("File Explorer", timeout=15):
            return "[Error] File Explorer did not open"
        time.sleep(0.8)

        # 2. Navigate to file location
        pyautogui.hotkey("ctrl", "l")
        time.sleep(0.3)
        pyperclip.copy(os.path.join(os.path.expanduser("~"), "Downloads"))
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.2)
        pyautogui.press("enter")
        time.sleep(2.0)   # wait for folder to load

        # 3. Select file
        pyautogui.typewrite(file_name, interval=0.05)
        time.sleep(0.5)
        pyautogui.press("enter")
        time.sleep(0.5)

        # 4. Copy file
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.5)

        # 5. Navigate to destination folder
        pyautogui.hotkey("ctrl", "l")
        time.sleep(0.3)
        pyperclip.copy(os.path.join(os.path.expanduser("~"), destination_folder))
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.2)
        pyautogui.press("enter")
        time.sleep(2.0)   # wait for folder to load

        # 6. Paste file
        pyautogui.hotkey("ctrl", "v")
        time.sleep(1.0)

        return "[Success] File moved to Documents folder"
    except Exception as e:
        return f"[Error] {str(e)}"