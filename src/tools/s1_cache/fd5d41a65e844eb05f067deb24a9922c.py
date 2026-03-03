"""
Cached S1-Grade code for: craete a pdf file with a text "HI"
Generated: 2026-02-26 12:36
"""

def execute(params: dict) -> str:
    try:
        text = params.get("text", "HI")
        desktop.open_application("Notepad")
        if not wait_for_window("Notepad", timeout=15):
            return "[Error] Notepad did not open"
        time.sleep(0.5)
        pyperclip.copy(text)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.3)
        pyautogui.hotkey("ctrl", "s")
        time.sleep(0.3)
        pyautogui.typewrite("output.pdf")
        time.sleep(0.3)
        pyautogui.press("enter")
        time.sleep(1.0)
        desktop.close_application("Notepad")
        return "[Success] PDF file created with text: " + text
    except Exception as e:
        return "[Error] " + str(e)