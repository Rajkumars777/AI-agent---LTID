import pygetwindow as gw
import time
import sys
import os

# Ensure backend is in path
sys.path.append(os.path.abspath("backend"))

from capabilities.desktop_automation import desktop_agent

def list_windows():
    print("--- Open Windows ---")
    windows = gw.getAllWindows()
    for w in windows:
        if w.visible:
            print(f"Title: '{w.title}'")
    print("--------------------")

def test_whatsapp_interaction():
    print("\n[Test] Checking for WhatsApp...")
    
    # Check if WhatsApp is open
    whatsapp_windows = gw.getWindowsWithTitle("WhatsApp")
    if not whatsapp_windows:
        print("❌ WhatsApp window not found via pygetwindow.")
        list_windows()
        return

    print(f"✅ Found {len(whatsapp_windows)} WhatsApp windows.")
    for w in whatsapp_windows:
        print(f" - '{w.title}' (Box: {w.left},{w.top} {w.width}x{w.height})")

    # Try to focus and type
    print("\n[Test] Attempting to type 'Debugging'...")
    try:
        result = desktop_agent.type_text("Debugging... ", window_title="WhatsApp")
        print(f"Result: {result}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    list_windows()
