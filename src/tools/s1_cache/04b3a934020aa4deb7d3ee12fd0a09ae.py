"""
Cached S1-Grade code for: open new.xlsx
Generated: 2026-02-25 09:49
"""

def execute(params: dict) -> str:
    try:
        app = params.get("app", "Excel")
        filename = params.get("text", "new.xlsx")

        desktop.open_application(app)
        if not wait_for_window(app, timeout=15):
            return f"[Error] {app} did not open"
        time.sleep(0.5)

        pyperclip.copy(filename)
        pyautogui.hotkey('ctrl', 'v')
        pyautogui.press('enter')
        time.sleep(1.0)

        return f"[Success] Opened {filename} in {app}"
    except Exception as e:
        return f"[Error] {str(e)}"