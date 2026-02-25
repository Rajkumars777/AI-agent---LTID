"""
app_templates.py
================
Pre-mapped UI coordinates for common applications.
Instant clicks with zero OCR overhead.
"""

import pygetwindow as gw
from typing import Optional, Dict, Tuple

# ── APP-SPECIFIC UI LAYOUTS ──
# Coordinates are relative to window (0,0 = top-left of app window)

APP_TEMPLATES: Dict[str, Dict[str, Tuple[int, int]]] = {
    
    "whatsapp": {
        "search_box":    (150, 60),   # "Search or start new chat"
        "message_input": (500, 950),  # "Type a message"
        "send_button":   (1200, 950), # Send arrow icon
        "attachment":    (400, 950),  # Paperclip icon
    },
    
    "gmail": {
        "compose":       (30, 150),   # "Compose" button
        "to_field":      (150, 250),  # Recipient field
        "subject_field": (150, 320),  # Subject line
        "body_field":    (150, 400),  # Email body
        "send_button":   (150, 950),  # Send button
        "search_box":    (600, 80),   # Search mail
    },
    
    "outlook": {
        "new_email":     (50, 100),
        "to_field":      (200, 200),
        "subject_field": (200, 250),
        "body_field":    (200, 350),
        "send_button":   (200, 100),
    },
    
    "chrome": {
        "address_bar":   (400, 50),
        "new_tab":       (100, 20),
        "search_box":    (500, 300),  # Google homepage
    },
}


class AppTemplate:
    """Fast UI interaction using pre-mapped coordinates."""
    
    @staticmethod
    def click_element(
        app_name: str,
        element_name: str,
        window_title: Optional[str] = None
    ) -> str:
        """
        Click an element using template coordinates.
        
        Speed: 0.05 seconds (instant)
        vs OCR: 2-3 seconds
        
        Example:
            AppTemplate.click_element("whatsapp", "search_box")
        """
        app_lower = app_name.lower()
        
        if app_lower not in APP_TEMPLATES:
            return f"❌ No template for '{app_name}'"
        
        template = APP_TEMPLATES[app_lower]
        
        if element_name not in template:
            return f"❌ Element '{element_name}' not in {app_name} template"
        
        # Get relative coordinates
        rel_x, rel_y = template[element_name]
        
        # Get window position
        try:
            wins = gw.getWindowsWithTitle(window_title or app_name)
            if not wins:
                return f"❌ Window not found: {window_title or app_name}"
            
            win = wins[0]
            abs_x = win.left + rel_x
            abs_y = win.top + rel_y
            
            # Click
            import pyautogui
            pyautogui.click(abs_x, abs_y)
            
            return f"✅ Clicked {app_name}.{element_name} at ({abs_x}, {abs_y})"
            
        except Exception as e:
            return f"❌ Template click failed: {e}"
