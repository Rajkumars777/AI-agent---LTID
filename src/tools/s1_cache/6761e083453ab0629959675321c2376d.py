"""
Cached S1-Grade code for: create new file sample.xlsx in Music
Generated: 2026-02-25 09:10
"""

def execute(params: dict) -> str:
    try:
        filename = "sample.xlsx"
        directory = "Music"

        desktop.open_application("Excel")
        if not wait_for_window("Excel", timeout=15):
            return "[Error] Excel did not open"
        time.sleep(0.8)

        pyautogui.hotkey("ctrl", "n")
        time.sleep(0.5)

        pyautogui.hotkey("ctrl", "s")
        time.sleep(0.3)

        pyperclip.copy(directory)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.3)
        pyautogui.press("enter")
        time.sleep(0.3)

        pyperclip.copy(filename)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.3)
        pyautogui.press("enter")
        time.sleep(0.3)

        return f"[Success] File {filename} created in {directory}"
    except Exception as e:
        return f"[Error] {str(e)}"