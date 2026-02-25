"""
Cached S1-Grade code for: open excel
Generated: 2026-02-25 12:02
"""

def execute(params: dict) -> str:
    try:
        app = params.get("app", "Excel")
        desktop.open_application(app)
        if not wait_for_window(app, timeout=15):
            return f"[Error] {app} did not open"
        time.sleep(0.5)
        return f"[Success] {app} opened"
    except Exception as e:
        return f"[Error] {str(e)}"