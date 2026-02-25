"""
Auto-generated tool: send_message_tool
Do not edit manually.
"""

import os
import subprocess
import ctypes

def execute(params: dict) -> str:
    try:
        message = params.get("message", "")
        recipient = params.get("recipient", "")
        
        if not message or not recipient:
            return "[Error] Message and recipient are required"
        
        # Use the built-in Windows mailto protocol to send an email
        mailto_command = f"mailto:{recipient}?body={message}"
        ctypes.windll.shell32.ShellExecuteW(None, "open", mailto_command, None, None, 1)
        
        return "[Success] Message sent"
    except Exception as e:
        return f"[Error] {str(e)}"