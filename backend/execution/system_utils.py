import time
import subprocess
import pygetwindow as gw
import pyautogui
import asyncio

def wait_for_window_focus(app_name, timeout=10):
    """
    Polls until the application window is active and ready to receive input.
    """
    start_time = time.time()
    print(f"DEBUG: Waiting for focus on window matching '{app_name}'...")
    while time.time() - start_time < timeout:
        try:
            active_window = gw.getActiveWindow()
            if active_window:
                # Check title match (case-insensitive)
                if app_name.lower() in active_window.title.lower():
                    print(f"DEBUG: Window '{active_window.title}' is active.")
                    return True
        except Exception:
            pass
        time.sleep(0.1) # Check every 100ms
    
    print(f"Warning: {app_name} did not focus in time (Timeout {timeout}s).")
    return False

def open_app(app_name):
    """
    Opens an application using the existing capability logic or subprocess.
    """
    # We reuse the desktop capability logic if possible, or simple subprocess
    # For now, simplistic approach as per plan, but we should probably use the robust launch_application from capabilities.
    # However, the user plan implied a simple open_app. 
    # Let's import the robust one to be safe.
    from capabilities.desktop import launch_application
    print(f"DEBUG: Launching {app_name}...")
    launch_application(app_name)

import pyperclip

def type_text(text):
    """
    Types text using Clipboard Injection (Copy + Paste) for speed and reliability.
    This prevents 'race conditions' where the start of the text is lost.
    """
    try:
        # 1. Load text into the system clipboard
        pyperclip.copy(text)
        
        # 2. Safety Buffer (Wait for OS to update clipboard and app to be ready)
        # The caller (execute_generative_command) already waits for window focus + 1.0s warm-up.
        # But a tiny buffer here for clipboard sync is good practice.
        time.sleep(0.1)
        
        # 3. Simulate "Ctrl + V" (Paste)
        # We use pyautogui for the hotkey as we already have it.
        pyautogui.hotkey('ctrl', 'v')
        
    except Exception as e:
        print(f"Error pasting text: {e}")
        # Fallback to slow typing if clipboard fails
        print("Falling back to slow typing...")
        try:
            pyautogui.write(text, interval=0.01)
        except Exception as e2:
             print(f"Error typing fallback: {e2}")

async def execute_generative_command(app_name, prompt):
    """
    Orchestrates parallel app opening and content generation.
    """
    from execution.nlu import generate_text_content
    
    # START BOTH TASKS AT ONCE
    
    # Task 1: Open the App (IO Bound) - Run in thread to not block event loop
    print(f"DEBUG: Launching {app_name}...")
    open_app(app_name)
    
    # Task 2: Generate Content (CPU/Network Bound)
    print(f"DEBUG: Generating content for: {prompt}...")
    generated_text_future = asyncio.to_thread(generate_text_content, prompt)
    
    # Detect if target is a file (has extension)
    is_file = '.' in app_name and any(ext in app_name.lower() for ext in ['.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml'])
    
    # Wait for App to be Ready (The Polling Fix)
    is_ready = await asyncio.to_thread(wait_for_window_focus, app_name if not is_file else "Notepad")
    
    if is_ready:
        # Wait for text ONLY if app opened faster than LLM
        print("DEBUG: Window ready. Waiting for content generation...")
        
        # WARM-UP DELAY: Even if focused, app might need a moment to accept input
        # This prevents "The" -> "e" truncation issues.
        await asyncio.sleep(1.0)
        
        # If it's a file, move cursor to end for APPEND mode
        if is_file:
            print("DEBUG: File detected. Sending Ctrl+End to append...")
            pyautogui.hotkey('ctrl', 'End')
            await asyncio.sleep(0.2)  # Small delay after hotkey
        
        text_to_type = await generated_text_future
        
        # Execute Typing
        print(f"DEBUG: Typing content ({len(text_to_type)} chars)...")
        type_text(text_to_type)
        return f"Generated and typed text about '{prompt}' into {app_name}"
    else:
        return "Aborting: Target app never appeared or could not be focused."
