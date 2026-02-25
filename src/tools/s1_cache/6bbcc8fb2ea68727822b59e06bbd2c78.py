"""
Cached S1-Grade code for: close whatsapp
Generated: 2026-02-25 12:02
"""

def execute(params: dict) -> str:
    try:
        app = params.get("app", "WhatsApp")
        desktop.close_application(app)
        time.sleep(0.5)
        return f"[Success] {app} closed"
    except Exception as e:
        return f"[Error] {str(e)}"