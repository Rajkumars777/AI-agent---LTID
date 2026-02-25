"""
Cached S1-Grade code for: List all files in the downloads folder
Generated: 2026-02-25 09:39
"""

def execute(params: dict) -> str:
    try:
        desktop.open_application("File Explorer")
        if not wait_for_window("File Explorer", timeout=15):
            return "[Error] File Explorer did not open"
        time.sleep(0.8)

        pyautogui.hotkey("ctrl", "e")  # focus address bar
        time.sleep(0.3)
        pyperclip.copy("C:\\Users\\%s\\Downloads" % os.getlogin())
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.2)
        pyautogui.press("enter")
        time.sleep(2.0)   # wait for downloads folder to load

        pyautogui.hotkey("ctrl", "a")  # select all files
        time.sleep(0.3)
        pyautogui.hotkey("ctrl", "c")  # copy file names
        time.sleep(0.3)

        pyperclip.copy("")
        desktop.open_application("Notepad")
        if not wait_for_window("Notepad", timeout=15):
            return "[Error] Notepad did not open"
        time.sleep(0.8)

        pyautogui.hotkey("ctrl", "v")  # paste file names
        time.sleep(0.3)

        file_names = pyperclip.paste()
        return "[Success] Files in downloads folder: %s" % file_names
    except Exception as e:
        return "[Error] %s" % str(e)