import subprocess
import pyautogui
import platform
import os
import glob
import time
from capabilities.file_search_cache import FileSearchIndex

# Global cache instance (lazy initialization)
_file_cache = None

def get_file_cache():
    """
    Get or create the file search cache instance.
    
    Lazy initialization:
    - Loads cache from disk if available
    - Builds index if cache is missing or stale
    
    Returns:
        FileSearchIndex instance
    """
    global _file_cache
    if _file_cache is None:
        _file_cache = FileSearchIndex()
        
        # Try to load existing cache
        loaded = _file_cache.load_from_disk()
        
        # Build index if cache doesn't exist or is stale
        if not loaded or _file_cache.is_stale():
            print("🔄 Cache missing or stale, rebuilding index...")
            _file_cache.build_index()
    
    return _file_cache

def refresh_file_cache() -> str:
    """
    Manually trigger cache rebuild.
    
    Use when:
    - Files have been added/deleted outside the application
    - Cache seems out of sync
    
    Returns:
        Success message
    """
    cache = get_file_cache()
    cache.build_index()
    return "✅ File cache refreshed successfully"

def clear_file_cache() -> str:
    """
    Clear cache and force rebuild on next search.
    
    Returns:
        Success message
    """
    global _file_cache
    _file_cache = None
    return "✅ File cache cleared"

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
    """Close an application using taskkill with smart process detection."""
    # Map common names to process names
    process_map = {
        "word": "winword.exe",
        "excel": "excel.exe",
        "powerpoint": "powerpnt.exe",
        "ppt": "powerpnt.exe",
        "chrome": "chrome.exe",
        "notepad": "notepad.exe",
        "calc": "CalculatorApp.exe",
        "calculator": "CalculatorApp.exe",
        "edge": "msedge.exe",
        "vscode": "code.exe",
        "code": "code.exe",
        "spotify": "spotify.exe",
        "whatsapp": "WhatsApp.exe",  # Fixed: Windows Store app
        "teams": "Teams.exe",
        "slack": "slack.exe",
        "discord": "discord.exe",
        "telegram": "Telegram.exe",
        "firefox": "firefox.exe",
        "brave": "brave.exe",
        "opera": "opera.exe",
        "vlc": "vlc.exe",
        "zoom": "Zoom.exe",
    }
    
    target = app_name.lower().strip()
    
    # Try mapped name first
    image_name = process_map.get(target, f"{target}.exe")
    
    # === Step 1: Try direct kill ===
    try:
        result = subprocess.run(
            f"taskkill /F /IM {image_name}", 
            shell=True, check=True, 
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        return f"✅ Closed {target} ({image_name})"
    except subprocess.CalledProcessError:
        pass  # Try fallback
    
    # === Step 2: Smart detection - find process by partial name match ===
    try:
        # Get list of all running processes
        result = subprocess.run(
            "tasklist /FO CSV",
            shell=True, capture_output=True, text=True
        )
        
        # Look for processes containing our target
        found_processes = []
        for line in result.stdout.split('\n'):
            if target.lower() in line.lower():
                # Parse CSV format: "Image Name","PID",...
                parts = line.split(',')
                if parts:
                    proc_name = parts[0].strip('"')
                    if proc_name and ".exe" in proc_name.lower():
                        found_processes.append(proc_name)
        
        # Remove duplicates
        found_processes = list(set(found_processes))
        
        if found_processes:
            # Kill all matching processes
            closed = []
            for proc in found_processes:
                try:
                    subprocess.run(
                        f"taskkill /F /IM \"{proc}\"",
                        shell=True, check=True,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE
                    )
                    closed.append(proc)
                except:
                    pass
            
            if closed:
                return f"✅ Closed {target}: {', '.join(closed)}"
    except Exception as e:
        print(f"⚠️ Error finding process: {e}")
    
    return f"❌ Could not close {target}. Is it running?"


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
        # Different content, return structured data for agent to handle
        # We limit to 5 for the message, but return all (or top N) in the list
        files_list = "\n".join([f"- {m}" for m in matches[:5]])
        if len(matches) > 5:
            files_list += f"\n...and {len(matches)-5} more."
            
        return {
            "status": "multiple_files",
            "message": f"Found multiple different files matching '{filename}':\n{files_list}\n\nPlease specify full path or rename to be unique.",
            "files": matches[:10] # Limit options to 10 to avoid UI clutter
        }

def find_file_paths(filename: str) -> list[str]:
    """
    A1 HYBRID SEARCH: Find file paths using cache + smart fallback.
    
    Strategy:
    1. Check cache (0.1s) - Fast O(1) lookup
    2. If not found, check likely folders (Downloads/Desktop/Documents) - Handles "new files"
    3. Cache any newly found files for faster subsequent access
    4. Return results or empty list
    
    This solves "The New File Problem":
    - User downloads invoice.pdf
    - Cache doesn't have it yet (built 2 hours ago)
    - Smart fallback finds it in Downloads folder
    - File is immediately cached for next time!
    
    Performance:
    - Cache hit: <100ms
    - Cache miss + smart fallback: ~500ms (only scans 3 folders)
    - Second access: <100ms (now cached!)
    
    Args:
        filename: File to search for (case-insensitive)
    
    Returns:
        List of absolute file paths
    """
    cache = get_file_cache()
    
    # === STEP 1: Fast Cache Search ===
    matches = cache.search(filename)
    if matches:
        return matches
    
    # === STEP 2: Smart Fallback for "New Files" ===
    # If not in cache, quickly scan likely locations
    # This prevents user frustration when files aren't in index
    print(f"⚠️ File '{filename}' not in index. Checking recent folders...")
    
    user_home = os.path.expanduser("~")
    likely_paths = [
        os.path.join(user_home, "Downloads"),
        os.path.join(user_home, "Desktop"),
        os.path.join(user_home, "Documents")
    ]
    
    found_matches = []
    target_lower = filename.lower()
    
    # Clean target (remove noise words)
    noise_words = [" file", " document", " sheet", " workbook", " excel", " word", " ppt"]
    clean_target = target_lower
    for noise in noise_words:
        clean_target = clean_target.replace(noise, "")
    clean_target = clean_target.strip()
    if not clean_target:
        clean_target = target_lower
    
    for path in likely_paths:
        if not os.path.exists(path):
            continue
        
        try:
            # Non-recursive scan of top level (very fast, ~50ms per folder)
            for item in os.listdir(path):
                item_lower = item.lower()
                
                # Check for match
                if clean_target in item_lower or target_lower in item_lower:
                    full_path = os.path.join(path, item)
                    
                    # Only include files, not directories
                    if os.path.isfile(full_path):
                        found_matches.append(full_path)
                        
                        # === STEP 3: Cache for next time! ===
                        cache.add_to_cache(full_path)
        except PermissionError:
            # Skip if we can't read the folder
            continue
        except Exception as e:
            # Skip on any other error
            print(f"⚠️ Error scanning {path}: {e}")
            continue
    
    if found_matches:
        print(f"✅ Found {len(found_matches)} file(s) and cached for future access!")
    
    return found_matches


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

def delete_file(filename: str) -> str:
    """
    A1 SAFE DELETE: Move file to Recycle Bin/Trash instead of permanent deletion.
    This allows users to recover accidentally deleted files.
    """
    matches = find_file_paths(filename)
    
    if not matches:
        return f"File '{filename}' not found."
    
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
             return f"Found multiple files named '{filename}'. Please specify which one to delete:\n{files_list}"
        
        # If identical, delete all duplicates
        target_paths = matches
    else:
        target_paths = matches
        
    try:
        # A1 SAFETY IMPROVEMENT: Use send2trash instead of os.remove
        # Files go to Recycle Bin (Windows) or Trash (macOS/Linux) - recoverable!
        from send2trash import send2trash
        
        deleted_files = []
        for target_path in target_paths:
            send2trash(target_path)
            deleted_files.append(os.path.basename(target_path))
        
        if len(deleted_files) == 1:
            return f"✓ Moved '{deleted_files[0]}' to Recycle Bin (recoverable)."
        else:
            return f"✓ Moved {len(deleted_files)} duplicate files to Recycle Bin (recoverable)."
    except Exception as e:
        return f"Error deleting file: {str(e)}"


import shutil

def move_file(filename: str, destination: str) -> str:
    """Move a file to any folder (Documents, Downloads, or custom folders)."""
    user_home = os.path.expanduser("~")
    
    # === Step 1: Clean destination name ===
    # "music folder" → "music", "downloads folder" → "downloads"
    dest_clean = destination.lower().strip()
    noise_words = [" folder", " directory", " dir", " drive"]
    for noise in noise_words:
        dest_clean = dest_clean.replace(noise, "")
    dest_clean = dest_clean.strip()
    
    # === Step 2: Check predefined folders first ===
    dest_map = {
        "documents": os.path.join(user_home, "Documents"),
        "doc": os.path.join(user_home, "Documents"),
        "docs": os.path.join(user_home, "Documents"),
        "downloads": os.path.join(user_home, "Downloads"),
        "download": os.path.join(user_home, "Downloads"),
        "desktop": os.path.join(user_home, "Desktop"),
        "music": os.path.join(user_home, "Music"),
        "videos": os.path.join(user_home, "Videos"),
        "video": os.path.join(user_home, "Videos"),
        "pictures": os.path.join(user_home, "Pictures"),
        "picture": os.path.join(user_home, "Pictures"),
        "photos": os.path.join(user_home, "Pictures"),
        "onedrive": os.path.join(user_home, "OneDrive"),
        "google drive": os.path.join(user_home, "Google Drive"),
        "gdrive": os.path.join(user_home, "Google Drive"),
    }
    
    target_dir = dest_map.get(dest_clean)
    
    # === Step 3: If not predefined, search for the folder ===
    if not target_dir:
        # Check if it's a full/relative path
        if os.path.isdir(destination):
            target_dir = destination
        elif os.path.isdir(dest_clean):
            target_dir = dest_clean
        else:
            # Search in common parent folders
            search_locations = [
                user_home,
                os.path.join(user_home, "Documents"),
                os.path.join(user_home, "Desktop"),
                os.path.join(user_home, "Downloads"),
            ]
            
            found_folders = []
            for parent in search_locations:
                if not os.path.exists(parent):
                    continue
                try:
                    for item in os.listdir(parent):
                        item_path = os.path.join(parent, item)
                        if os.path.isdir(item_path) and dest_clean in item.lower():
                            found_folders.append(item_path)
                except PermissionError:
                    continue
            
            if len(found_folders) == 1:
                target_dir = found_folders[0]
            elif len(found_folders) > 1:
                folders_list = "\n".join([f"- {f}" for f in found_folders[:5]])
                return f"Found multiple folders matching '{dest_clean}':\n{folders_list}\nPlease specify the exact folder path."
    
    if not target_dir:
        available = ", ".join(sorted(dest_map.keys()))
        return f"❌ Folder '{destination}' not found. Available: {available}"
             
    # === Step 4: Find Source File ===
    matches = find_file_paths(filename)
    
    if not matches:
        return f"❌ File '{filename}' not found."
    
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
        
        source_path = matches[0]
    else:
        source_path = matches[0]
        
    # === Step 5: Move ===
    try:
        if not os.path.exists(target_dir):
            return f"❌ Destination directory does not exist: {target_dir}"
            
        file_basename = os.path.basename(source_path)
        dest_path = os.path.join(target_dir, file_basename)
        
        if os.path.exists(dest_path):
            return f"❌ A file named '{file_basename}' already exists in {os.path.basename(target_dir)}."
            
        shutil.move(source_path, dest_path)
        return f"✅ Moved '{file_basename}' to {os.path.basename(target_dir)}"
    except Exception as e:
        return f"❌ Error moving file: {str(e)}"


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
