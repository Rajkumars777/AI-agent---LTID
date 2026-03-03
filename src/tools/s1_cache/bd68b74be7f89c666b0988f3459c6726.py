"""
Cached S1-Grade code for: In the book1.xlsx file color the A1 column background into green
Generated: 2026-02-26 17:31
"""

def execute(params: dict) -> str:
    try:
        file_path = "book1.xlsx"
        desktop.open_application("Excel")
        if not wait_for_window("Excel", timeout=15):
            return "[Error] Excel did not open"
        time.sleep(0.8)

        # Open file
        pyautogui.hotkey("ctrl", "o")
        time.sleep(0.5)
        pyperclip.copy(file_path)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.2)
        pyautogui.press("enter")
        time.sleep(2.0)

        # Select A1 cell
        pyautogui.hotkey("ctrl", "home")
        time.sleep(0.2)
        pyautogui.press("right")
        time.sleep(0.2)

        # Open format cells dialog
        pyautogui.hotkey("ctrl", "1")
        time.sleep(0.5)

        # Select fill tab
        pyautogui.press("tab")
        time.sleep(0.2)
        pyautogui.press("tab")
        time.sleep(0.2)
        pyautogui.press("down")
        time.sleep(0.2)

        # Select green color
        pyautogui.press("tab")
        time.sleep(0.2)
        pyautogui.press("down")
        time.sleep(0.2)
        pyautogui.press("down")
        time.sleep(0.2)
        pyautogui.press("down")
        time.sleep(0.2)
        pyautogui.press("down")
        time.sleep(0.2)
        pyautogui.press("down")
        time.sleep(0.2)
        pyautogui.press("enter")
        time.sleep(0.5)

        # Close Excel
        pyautogui.hotkey("alt", "f4")
        time.sleep(0.2)
        pyautogui.press("enter")
        time.sleep(0.5)

        return "[Success] A1 cell background colored green"
    except Exception as e:
        return f"[Error] {str(e)}"