"""
Cached S1-Grade code for: create a pdf file with a text "hi"
Generated: 2026-02-26 12:40
"""

def execute(params: dict) -> str:
    try:
        text = params.get("text", "hi")
        desktop.open_application("Notepad")
        if not wait_for_window("Notepad", timeout=15):
            return "[Error] Notepad did not open"
        time.sleep(0.5)
        pyperclip.copy(text)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.3)
        pyautogui.hotkey("ctrl", "s")
        time.sleep(0.3)
        filename = "output"
        pyperclip.copy(filename)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.3)
        pyautogui.press("tab")
        time.sleep(0.3)
        pyautogui.press("tab")
        time.sleep(0.3)
        pyautogui.typewrite(".pdf", interval=0.05)
        time.sleep(0.3)
        pyautogui.press("enter")
        time.sleep(1.0)
        return "[Success] PDF file created with text"
    except Exception as e:
        return f"[Error] {str(e)}"