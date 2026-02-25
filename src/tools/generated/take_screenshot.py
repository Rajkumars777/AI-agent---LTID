"""
Auto-generated tool: take_screenshot
Do not edit manually.
"""

import os
import ctypes

def execute(params: dict) -> str:
    try:
        filename = params.get("filename", "screenshot.png")
        user32 = ctypes.windll.user32
        screensize = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
        hdc = user32.GetDC(0)
        mfc = ctypes.create_string_buffer(screensize[0] * screensize[1] * 4)
        user32.StretchBlt(hdc, 0, 0, screensize[0], screensize[1], hdc, 0, 0, screensize[0], screensize[1], 0x00CC0020)
        with open(filename, 'wb') as f:
            f.write(mfc.raw)
        return f"[Success] Screenshot saved as {filename}"
    except Exception as e:
        return f"[Error] {str(e)}"