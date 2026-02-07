import subprocess
import pyautogui
import platform
import os
import glob
import time

def get_start_menu_paths():
    """Get all common Windows Start Menu paths."""
    paths = [
        os.path.join(os.environ["ProgramData"], "Microsoft", "Windows", "Start Menu"),
        os.path.join(os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu"),
        # Sometimes apps are just in Roaming/Microsoft/Windows/Start Menu without 'Programs'
    ]
    return paths

def find_app_in_start_menu(app_name):
    """
    Search recursively for a .lnk file matching the app name.
    Returns the full path to the shortcut if found.
    """
    search_terms = app_name.lower().split() # e.g., "visual studio" -> ["visual", "studio"]
    
    for base_path in get_start_menu_paths():
        if not os.path.exists(base_path):
            continue
            
        for root, dirs, files in os.walk(base_path):
            for file in files:
                if file.lower().endswith(".lnk"):
                    filename = file.lower()
                    # Check if ALL search terms are in the filename (more loose matching)
                    # e.g., "word" matches "Microsoft Word.lnk"
                    if all(term in filename for term in search_terms):
                        return os.path.join(root, file)
    return None

import difflib

def launch_application(app_name: str) -> str:
    """
    Launch a desktop application.
    1. Tries common system aliases (fastest).
    2. Tries Fuzzy Matching (Spell Correction).
    3. Searches Windows Start Menu for shortcuts (robust).
    """
    system = platform.system()
    
    # 1. Extensive Alias Map
    app_map = {
        "ppt": "powerpnt",
        "powerpoint": "powerpnt",
        "word": "winword",
        "doc": "winword",
        "excel": "excel",
        "sheet": "excel",
        "calc": "calc",
        "calculator": "calc",
        "notepad": "notepad",
        "chrome": "chrome",
        "google": "chrome",
        "edge": "msedge",
        "vscode": "code",
        "code": "code",
        "explorer": "explorer",
        "file": "explorer",
        "cmd": "cmd",
        "terminal": "cmd",
        "ps": "powershell",
        "whatsapp": "whatsapp:",
        "spotify": "spotify:",
        "monitor": "taskmgr",
        "task": "taskmgr",
        "control": "control",
        "setting": "ms-settings:", # Settings app
        "settings": "ms-settings:",
        "xbox": "xbox:",
        "store": "ms-windows-store:",
        "camera": "microsoft.windows.camera:",
        "photo": "ms-photos:",
        "photos": "ms-photos:",
        "videos": "explorer shell:MyVideo",
        "video": "explorer shell:MyVideo",
        "music": "explorer shell:MyMusic",
        "documents": "explorer shell:Personal",
        "document": "explorer shell:Personal",
        "downloads": "explorer shell:Downloads",
        "download": "explorer shell:Downloads",
        "pictures": "explorer shell:MyPictures",
        "picture": "explorer shell:MyPictures",
        "desktop": "explorer shell:Desktop",
    }
    
    target = app_name.lower().strip()
    
    # Direct command attempt
    cmd = app_map.get(target)
    
    # If not found directly, try fuzzy match
    correction = None
    if not cmd:
        matches = difflib.get_close_matches(target, app_map.keys(), n=1, cutoff=0.7)
        if matches:
            correction = matches[0]
            cmd = app_map[correction]
    
    # If still no cmd, use target as is (for start search)
    if not cmd:
        cmd = target

    try:
        if system == "Windows":
            # A. Try Protocol / Direct Command / Alias
            try:
                # If it looks like a protocol (ends in :) or is a known command/alias
                is_protocol = cmd.endswith(":")
                is_alias = (target in app_map) or (correction is not None)
                
                if is_protocol or is_alias:
                    subprocess.Popen(f"start {cmd}", shell=True)
                    if correction:
                        return f"Corrected '{target}' to '{correction}' and launched it."
                    return f"Launched {target}"
            except:
                pass 

            # B. Search Start Menu (The "Find it anywhere" approach)
            if not correction: # Only search if we didn't already find a correction
                shortcut = find_app_in_start_menu(target)
                if shortcut:
                    os.startfile(shortcut)
                    return f"Launched {target} (found in Start Menu)"
            
            # C. Last ditch: Just run it and hope 'start' finds it in PATH
            
            # FIX: If target has spaces (and isn't a valid path), 'start' will likely fail and show a Popup Error.
            # So checking for spaces or dots is crucial.
            if (" " in target or "." in target) and not os.path.exists(target) and not os.path.isabs(target):
                 # It's likely a sentence or a file name, not a command in PATH.
                 # Fallback to file search without risking a popup.
                 return f"Application '{target}' is not in the system (skipped auto-launch to avoid popup)."

            process = subprocess.Popen(f"start {cmd}", shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            # Give it a moment? No, start returns immediately.
            
            # Since we can't be 100% sure 'start' succeeded visually, we optimize for "Best Effort".
            # But the user wants a reply if NOT in system.
            # If step B failed and C is just a guess, we might want to be honest.
            
            if not is_alias and not is_protocol and not shortcut:
                 return f"Application '{target}' is not in the system (or not found in Start Menu)."
            
            return f"Launched {target}"

        elif system == "Darwin": # macOS
            subprocess.Popen(["open", "-a", target])
            return f"Launched {target}"
        elif system == "Linux":
            subprocess.Popen([target])
            return f"Launched {target}"
        else:
            return "OS not supported for auto-launch"
    except Exception as e:
        return f"Error launching {target}: {str(e)}"

import hashlib

def close_application(app_name: str) -> str:
    """Close an application using taskkill."""
    # Map common names to process names
    process_map = {
        "word": "winword.exe",
        "excel": "excel.exe",
        "powerpoint": "powerpnt.exe",
        "ppt": "powerpnt.exe",
        "chrome": "chrome.exe",
        "notepad": "notepad.exe",
        "calc": "CalculatorApp.exe", # Windows 10/11 Calculator
        "calculator": "CalculatorApp.exe",
        "edge": "msedge.exe",
        "vscode": "code.exe",
        "code": "code.exe",
        "spotify": "spotify.exe",
        "whatsapp": "whatsapp.exe",
    }
    
    target = app_name.lower().strip()
    image_name = process_map.get(target, f"{target}.exe")
    
    try:
        # /F = Force, /IM = Image Name
        subprocess.run(f"taskkill /F /IM {image_name}", shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return f"Closed {target} ({image_name})"
    except subprocess.CalledProcessError:
        return f"Could not close {target}. Is it running?"

def get_file_hash(filepath: str) -> str:
    """Calculate MD5 hash of a file to check for duplicates."""
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            buf = f.read(65536)
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(65536)
        return hasher.hexdigest()
    except:
        return "error_hashing"

def find_and_open_file(filename: str) -> str:
    """
    Search for a file in the User's Home Directory (Recursive).
    Includes Desktop, Documents, Downloads, OneDrive, etc.
    Excludes AppData and hidden folders for speed.
    """
    user_home = os.path.expanduser("~")
    
    matches = []
    target_name = filename.lower()
    
    # Pre-process target name to remove noise words
    # e.g., "sample excel file" -> "sample"
    noise_words = [" file", " document", " sheet", " workbook", " excel", " word", " ppt"]
    clean_target = target_name
    for noise in noise_words:
        clean_target = clean_target.replace(noise, "")
    
    clean_target = clean_target.strip()
    if not clean_target: clean_target = target_name

    # Walk the entire user home directory
    for root, dirs, files in os.walk(user_home):
        # Exclude hidden directories and AppData
        dirs[:] = [d for d in dirs if not d.startswith('.') and d.lower() != 'appdata']
        
        for file in files:
            # Check 1: Exact match with clean target (ignoring extension logic handled by 'in')
            # Check 2: target name in filename
            
            # If user said "sample.xlsx", clean_target is "sample.xlsx". 
            # If "sample excel file", clean_target is "sample".
            
            f_lower = file.lower()
            if clean_target in f_lower:
                matches.append(os.path.join(root, file))
                    
    if not matches:
        return f"File '{filename}' not found in {user_home} (and subfolders)."
    
    # 2. Analyze Matches
    if len(matches) == 1:
        os.startfile(matches[0])
        return f"Opened: {matches[0]}"
    
    # Multiple matches found
    first_hash = get_file_hash(matches[0])
    all_identical = True
    
    for match in matches[1:]:
        if get_file_hash(match) != first_hash:
            all_identical = False
            break
            
    if all_identical:
        # If all are same content, just open the first one
        os.startfile(matches[0])
        return f"Found {len(matches)} copies of the same file. Opened: {matches[0]}"
    else:
        # Different content, ask user
        # Format list nicely
        # We can implement a smarter selection here, but for now list them.
        files_list = "\n".join([f"- {m}" for m in matches[:5]]) # Limit to 5
        if len(matches) > 5:
            files_list += f"\n...and {len(matches)-5} more."
            
        return f"Found multiple different files matching '{filename}':\n{files_list}\n\nPlease specify full path or rename to be unique."

def find_file_paths(filename: str) -> list[str]:
    """Helper to find all file paths matching a name."""
    user_home = os.path.expanduser("~")
    matches = []
    target_name = filename.lower()
    
    for root, dirs, files in os.walk(user_home):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d.lower() != 'appdata']
        for file in files:
            if target_name == file.lower(): # Exact match for rename preference, or partial? Let's do exact for rename to be safe
                matches.append(os.path.join(root, file))
            elif target_name in file.lower():
                 pass # For open we accept partial, for rename maybe we should be stricter? 
                 # Let's stick to the current logic: "find_and_open" uses partial.
                 # "rename" should probably find the best match.
    
    # Re-implementing loose match for consistency if exact failed
    if not matches:
        for root, dirs, files in os.walk(user_home):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d.lower() != 'appdata']
            for file in files:
                if target_name in file.lower():
                    matches.append(os.path.join(root, file))
    
    return matches

def rename_file(old_name: str, new_name: str) -> str:
    """Rename a file in user/system folders."""
    matches = find_file_paths(old_name)
    
    if not matches:
        return f"File '{old_name}' not found."
    
    if len(matches) > 1:
        # Check if they are duplicates
        first_hash = get_file_hash(matches[0])
        all_identical = True
        for m in matches[1:]:
            if get_file_hash(m) != first_hash:
                all_identical = False
                break
        
        if not all_identical:
             files_list = "\n".join([f"- {m}" for m in matches[:5]])
             return f"Found multiple files named '{old_name}'. Please verify which one to rename:\n{files_list}"
        
        # If identical, rename the first one? Or all? 
        # Safest is to just rename the first found or ask user.
        # Let's rename the first one found for now.
        target_path = matches[0]
    else:
        target_path = matches[0]
        
    try:
        dirname = os.path.dirname(target_path)
        new_path = os.path.join(dirname, new_name)
        
        if os.path.exists(new_path):
            return f"Error: A file named '{new_name}' already exists in {dirname}."
            
        os.rename(target_path, new_path)
        return f"Successfully renamed '{os.path.basename(target_path)}' to '{new_name}'."
    except Exception as e:
        return f"Error renaming file: {str(e)}"

import shutil

def move_file(filename: str, destination: str) -> str:
    """Move a file to a system folder (Documents, Downloads, etc.)."""
    # 1. Resolve Destination
    user_home = os.path.expanduser("~")
    dest_map = {
        "documents": os.path.join(user_home, "Documents"),
        "doc": os.path.join(user_home, "Documents"),
        "downloads": os.path.join(user_home, "Downloads"),
        "download": os.path.join(user_home, "Downloads"),
        "desktop": os.path.join(user_home, "Desktop"),
        "music": os.path.join(user_home, "Music"),
        "videos": os.path.join(user_home, "Videos"),
        "video": os.path.join(user_home, "Videos"),
        "pictures": os.path.join(user_home, "Pictures"),
        "picture": os.path.join(user_home, "Pictures"),
        "onedrive": os.path.join(user_home, "OneDrive"),
    }
    
    target_dir = dest_map.get(destination.lower().strip())
    
    # If not a keyword, maybe it's a full path?
    if not target_dir:
        if os.path.isdir(destination):
            target_dir = destination
        else:
             return f"Unknown destination folder '{destination}'. Try 'Documents', 'Desktop', 'Downloads', etc."
             
    # 2. Find Source File
    matches = find_file_paths(filename)
    
    if not matches:
        return f"File '{filename}' not found."
    
    if len(matches) > 1:
        # Check for duplicates using hash
        first_hash = get_file_hash(matches[0])
        all_identical = True
        for m in matches[1:]:
            if get_file_hash(m) != first_hash:
                all_identical = False
                break
                
        if not all_identical:
             files_list = "\n".join([f"- {m}" for m in matches[:5]])
             return f"Found multiple different files named '{filename}'. Please specify full path:\n{files_list}"
        
        # Identical? Pick first.
        source_path = matches[0]
    else:
        source_path = matches[0]
        
    # 3. Move
    try:
        if not os.path.exists(target_dir):
            return f"Destination directory does not exist: {target_dir}"
            
        file_basename = os.path.basename(source_path)
        dest_path = os.path.join(target_dir, file_basename)
        
        if os.path.exists(dest_path):
            return f"Error: A file named '{file_basename}' already exists in {destination}."
            
        shutil.move(source_path, dest_path)
        return f"Successfully moved '{file_basename}' to {destination}."
    except Exception as e:
        return f"Error moving file: {str(e)}"

def type_text(text: str, interval: float = 0.05) -> str:
    """Type text into the currently active window."""
    try:
        pyautogui.write(text, interval=interval)
        return f"Typed: {text}"
    except Exception as e:
        return f"Error typing text: {str(e)}"

def send_key(key: str) -> str:
    """Simulate a key press (e.g., 'enter', 'esc')."""
    try:
        pyautogui.press(key)
        return f"Sent Key: {key}"
    except Exception as e:
        return f"Error sending key {key}: {str(e)}"
