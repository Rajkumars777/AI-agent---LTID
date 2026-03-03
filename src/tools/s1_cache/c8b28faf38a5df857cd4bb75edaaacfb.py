"""
Cached S1-Grade code for: In the Bokk1.xlsx file color the A1 column background into green
Generated: 2026-02-26 17:30
"""

def execute(params: dict) -> str:
    try:
        file_path = params.get("file_path", "Bokk1.xlsx")
        desktop.open_application("Excel")
        if not wait_for_window("Excel", timeout=15):
            return "[Error] Excel did not open"
        time.sleep(0.8)

        pyautogui.hotkey("ctrl", "o")
        time.sleep(0.5)
        pyperclip.copy(file_path)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.2)
        pyautogui.press("enter")
        time.sleep(2.0)

        pyautogui.hotkey("ctrl", "home")
        time.sleep(0.3)
        pyautogui.hotkey("alt", "h")
        time.sleep(0.3)
        pyautogui.hotkey("h", "f", "g")
        time.sleep(0.3)
        pyautogui.press("enter")
        time.sleep(0.3)

        return "[Success] A1 column background colored green"
    except Exception as e:
        return f"[Error] {str(e)}"