"""
Cached S1-Grade code for: open brave browser and search gmail and send mail hi to rajcsecs@gmail.com
Generated: 2026-02-24 23:50
"""

def execute(params: dict) -> str:
    try:
        browser   = params.get("browser", "Brave")
        recipient = params.get("recipient", "rajcsecs@gmail.com")
        subject   = params.get("subject", "No Subject")
        body      = params.get("body", "hi")

        desktop.open_application(browser)
        if not wait_for_window(browser, timeout=15):
            return f"[Error] {browser} did not open"
        time.sleep(0.8)

        pyautogui.hotkey("ctrl", "t")
        time.sleep(0.5)

        pyautogui.hotkey("ctrl", "l")
        time.sleep(0.3)
        pyperclip.copy("https://mail.google.com")
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.2)
        pyautogui.press("enter")
        time.sleep(4.0)

        pyautogui.press("c")
        time.sleep(2.5)

        pyperclip.copy(recipient)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.5)
        pyautogui.press("tab")
        time.sleep(0.3)

        pyperclip.copy(subject)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.3)
        pyautogui.press("tab")
        time.sleep(0.3)

        pyperclip.copy(body)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.3)

        pyautogui.hotkey("ctrl", "enter")
        time.sleep(1.5)

        return f"[Success] Email sent to {recipient} via Gmail"
    except Exception as e:
        return f"[Error] {str(e)}"