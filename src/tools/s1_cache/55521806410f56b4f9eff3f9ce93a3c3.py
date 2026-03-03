"""
Cached S1-Grade code for: In the book1.xlsx file color the A column into green colour
Generated: 2026-02-26 17:32
"""

def execute(params: dict) -> str:
    try:
        file_name = "book1.xlsx"
        desktop.open_application("Excel")
        if not wait_for_window("Excel", timeout=15):
            return "[Error] Excel did not open"
        time.sleep(0.8)

        # Open the file
        pyautogui.hotkey("ctrl", "o")
        time.sleep(0.5)
        pyperclip.copy(file_name)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.2)
        pyautogui.press("enter")
        time.sleep(2.0)   # wait for file to open

        # Select the A column
        pyautogui.hotkey("ctrl", "space")
        time.sleep(0.2)
        pyautogui.press("a")
        time.sleep(0.2)

        # Open the Home tab
        pyautogui.press("home")
        time.sleep(0.2)

        # Open the Fill Color menu
        pyautogui.hotkey("alt", "h")
        time.sleep(0.2)
        pyautogui.press("f")
        time.sleep(0.2)

        # Select the green color
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
        pyautogui.press("down")
        time.sleep(0.2)
        pyautogui.press("down")
        time.sleep(0.2)
        pyautogui.press("down")
        time.sleep(0.2)
        pyautogui.press("enter")
        time.sleep(0.2)

        return "[Success] A column colored green in book1.xlsx"
    except Exception as e:
        return f"[Error] {str(e)}"