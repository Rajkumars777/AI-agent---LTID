"""
src/services/desktop/ops.py
============================
App & File open/close using Windows Start Menu visual search as primary method.

Open Strategy:
  1. Focus existing window  → instant if already running
  2. Start Menu search      → types name visibly, waits for results, presses Enter
                              Works for ALL apps + files in standard folders
  3. file_index fallback    → for files in custom/non-indexed paths

Close Strategy:
  1. Graceful window close via pygetwindow (sends WM_CLOSE — app can save first)
  2. Force process kill via psutil (hard terminate)

File ops (rename/move/copy/delete/list):
  → resolve_target_path()  uses file_index cache for fast lookup
"""

import os
import time
import shutil
from typing import Optional, Dict

from src.services.desktop.file_index import file_index

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

USERPROFILE = os.environ.get("USERPROFILE", os.path.expanduser("~"))

USER_FOLDERS: Dict[str, str] = {
    "desktop":   os.path.join(USERPROFILE, "Desktop"),
    "documents": os.path.join(USERPROFILE, "Documents"),
    "downloads": os.path.join(USERPROFILE, "Downloads"),
    "music":     os.path.join(USERPROFILE, "Music"),
    "pictures":  os.path.join(USERPROFILE, "Pictures"),
    "videos":    os.path.join(USERPROFILE, "Videos"),
    "onedrive":  os.path.join(USERPROFILE, "OneDrive"),
}

APP_ALIASES: Dict[str, Dict[str, str]] = {
    "word":       {"proc": "WINWORD.EXE",       "title": "Word"},
    "excel":      {"proc": "EXCEL.EXE",          "title": "Excel"},
    "powerpoint": {"proc": "POWERPNT.EXE",       "title": "PowerPoint"},
    "chrome":     {"proc": "chrome.exe",          "title": "Chrome"},
    "firefox":    {"proc": "firefox.exe",         "title": "Firefox"},
    "edge":       {"proc": "msedge.exe",          "title": "Edge"},
    "notepad":    {"proc": "notepad.exe",         "title": "Notepad"},
    "calculator": {"proc": "calc.exe",             "title": "Calculator"},
    "calc":       {"proc": "calc.exe",             "title": "Calculator"},
    "spotify":    {"proc": "Spotify.exe",         "title": "Spotify"},
    "whatsapp":   {"proc": "WhatsApp.exe",        "title": "WhatsApp"},
    "teams":      {"proc": "Teams.exe",           "title": "Microsoft Teams"},
    "outlook":    {"proc": "OUTLOOK.EXE",         "title": "Outlook"},
    "vscode":     {"proc": "Code.exe",            "title": "Visual Studio Code"},
    "code":       {"proc": "Code.exe",            "title": "Visual Studio Code"},
    "paint":      {"proc": "mspaint.exe",         "title": "Paint"},
    "explorer":   {"proc": "explorer.exe",        "title": "File Explorer"},
    "cmd":        {"proc": "cmd.exe",             "title": "Command Prompt"},
    "terminal":   {"proc": "WindowsTerminal.exe", "title": "Windows Terminal"},
    "vlc":        {"proc": "vlc.exe",             "title": "VLC"},
    "zoom":       {"proc": "Zoom.exe",            "title": "Zoom"},
    "discord":    {"proc": "Discord.exe",         "title": "Discord"},
    "telegram":   {"proc": "Telegram.exe",        "title": "Telegram"},
    "brave":      {"proc": "brave.exe",           "title": "Brave"},
    "winrar":     {"proc": "WinRAR.exe",          "title": "WinRAR"},
    "7zip":       {"proc": "7zFM.exe",            "title": "7-Zip"},
    "taskmgr":    {"proc": "Taskmgr.exe",         "title": "Task Manager"},
}





def is_known_app(name: str) -> bool:
    """Check if the name matches a known application alias."""
    name_lower = name.lower().strip()
    return name_lower in APP_ALIASES


def _expand_alias(target: str) -> str:
    """Expand 'music/song.mp3' or 'desktop' → full absolute path."""
    lower = target.lower().replace("\\", "/")
    for alias, folder in USER_FOLDERS.items():
        if lower == alias:
            return folder
        if lower.startswith(f"{alias}/"):
            return os.path.join(folder, target[len(alias) + 1:])
    return target


def resolve_target_path(target: str) -> Optional[str]:
    """
    Resolve a file/folder name to its full absolute path.
    Used by rename, move, copy, delete — NOT by open (which uses Start Menu).

    Stage 1: Alias expansion + direct path check
    Stage 2: file_index in-memory cache (fast, covers all user + program folders)
    """
    if not target or not target.strip():
        return None

    target = target.strip()

    # Stage 1: Alias expansion + direct path
    expanded = _expand_alias(target)
    if os.path.exists(expanded):
        return os.path.abspath(expanded)

    # Stage 2: File index cache
    results = file_index.search(target, limit=5)
    if results:
        for r in results:
            if os.path.basename(r).lower() == os.path.basename(target).lower():
                return r
        return results[0]

    return None


# ─────────────────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────────────
# FOCUS — bring existing window to front
# ─────────────────────────────────────────────────────────────────────────────

def focus_application(target: str) -> bool:
    """
    Bring an already-running app window to the front.
    Returns True if found and focused — skips re-launching.
    """
    try:
        import pygetwindow as gw

        target_lower = target.lower().strip()
        title_key    = target_lower

        for alias, info in APP_ALIASES.items():
            if alias in target_lower:
                title_key = info["title"].lower()
                break

        for win in gw.getAllWindows():
            if win.title and (
                title_key    in win.title.lower() or
                target_lower in win.title.lower()
            ):
                try:
                    if win.isMinimized:
                        win.restore()
                    win.activate()
                    time.sleep(0.3)
                    print(f"[Focus] Focused: '{win.title}'")
                    return True
                except Exception:
                    continue
    except Exception:
        pass
    return False


# ─────────────────────────────────────────────────────────────────────────────
# OPEN
# ─────────────────────────────────────────────────────────────────────────────

def open_application(target: str) -> str:
    """
    Open any app or file by name, alias, or path directly.

    Strategy:
      - FILES (has extension like .xlsx, .pdf, etc.) → always use os.startfile
        with the full resolved path. NEVER focus an existing app window.
      - APPS (no extension) → focus existing window first, then Start Menu.
    """
    target = target.strip()

    # ── Detect if this is a FILE (has a data-file extension) ──
    FILE_EXTENSIONS = {
        ".xlsx", ".xls", ".csv", ".pdf", ".txt", ".docx", ".doc",
        ".pptx", ".ppt", ".png", ".jpg", ".jpeg", ".gif", ".bmp",
        ".mp3", ".mp4", ".wav", ".avi", ".mkv", ".zip", ".rar",
        ".json", ".xml", ".html", ".py", ".js", ".ts", ".css",
    }
    _, ext = os.path.splitext(target)
    is_file = ext.lower() in FILE_EXTENSIONS

    # Also treat full absolute paths as files
    if os.path.isabs(target) and os.path.exists(target):
        is_file = True

    if is_file:
        # ── FILE PATH: resolve and open directly, never focus random windows ──
        print(f"[Open] FILE detected: '{target}' — resolving path and using os.startfile")

        # 1. Direct path or alias expansion
        expanded = _expand_alias(target)
        if os.path.exists(expanded):
            try:
                os.startfile(expanded)
                return f"✅ Opened: {os.path.basename(expanded)}"
            except Exception as e:
                return f"❌ Could not open '{expanded}': {e}"

        # 2. file_index lookup
        path = resolve_target_path(target)
        if path and os.path.exists(path):
            try:
                os.startfile(path)
                return f"✅ Opened: {os.path.basename(path)}"
            except Exception as e:
                return f"❌ Could not open '{path}': {e}"

        # 3. File not found anywhere
        return f"❌ File not found: '{target}'. Check the name and try again."

    # ── APPLICATION: focus if running, then Start Menu ──
    print(f"[Open] APP detected: '{target}' — trying focus, then Start Menu")

    # Step 1: Already running? Just focus it
    if focus_application(target):
        return f"✅ Switched to running: '{target}'"

    # Step 2: Try subprocess start for known apps
    import subprocess
    target_lower = target.lower()
    proc_name = None
    for alias, info in APP_ALIASES.items():
        if alias in target_lower:
            proc_name = info["proc"]
            break

    if proc_name:
        import shutil
        # Verify the executable actually exists on the system before trying
        if shutil.which(proc_name) or os.path.exists(proc_name):
            try:
                print(f"[Open] Attempting subprocess start for known app: {proc_name}")
                subprocess.Popen(f"start \"\" \"{proc_name}\"", shell=True)
                return f"✅ Opened: '{proc_name}'"
            except Exception as e:
                print(f"[Open] Subprocess start failed: {e}")
        else:
            print(f"[Open] Executable '{proc_name}' not found on PATH — skipping to Start Menu")

    # Step 3: Start Menu search (works for all installed apps)
    print(f"[Open] Using Start Menu search for '{target}'")
    from src.services.desktop.automation import desktop_agent
    return desktop_agent.search_start_menu(target, "open")


# ─────────────────────────────────────────────────────────────────────────────
# CLOSE
# ─────────────────────────────────────────────────────────────────────────────

def close_application(target: str) -> str:
    """
    Close a running app by window title or name.

    Step 1 → Graceful window close via pygetwindow  (app can save unsaved work)
    Step 2 → Force process kill via psutil           (hard terminate if Step 1 fails)
    """
    try:
        import pygetwindow as gw
        import psutil
    except ImportError:
        return "❌ Missing libraries: install pygetwindow and psutil."

    target_lower = target.lower().strip()
    title_key    = target_lower
    proc_name    = None

    for alias, info in APP_ALIASES.items():
        if alias in target_lower:
            title_key = info["title"].lower()
            proc_name = info["proc"]
            break

    # Step 1: Graceful window close (WM_CLOSE — app gets a chance to save)
    closed = 0
    try:
        for win in gw.getAllWindows():
            if win.title and (
                title_key    in win.title.lower() or
                target_lower in win.title.lower()
            ):
                try:
                    win.close()
                    closed += 1
                    print(f"[Close] Gracefully closed: '{win.title}'")
                except Exception:
                    pass
    except Exception as e:
        print(f"[Close] Window close error: {e}")

    if closed > 0:
        return f"✅ Closed {closed} window(s) matching '{target}'."

    # Step 2: Force kill process
    if not proc_name:
        proc_name = target_lower if target_lower.endswith(".exe") else f"{target_lower}.exe"

    killed = 0
    try:
        for proc in psutil.process_iter(["name"]):
            if proc.info["name"] and proc.info["name"].lower() == proc_name.lower():
                proc.kill()
                killed += 1
                print(f"[Close] Force-killed process: '{proc.info['name']}'")
    except Exception as e:
        return f"❌ Process kill error: {e}"

    if killed > 0:
        return f"✅ Force-terminated {killed} process(es) matching '{target}'."

    return f"❌ No running window or process found matching '{target}'."


# ─────────────────────────────────────────────────────────────────────────────
# FILE OPERATIONS
# ─────────────────────────────────────────────────────────────────────────────

def rename_file(target: str, new_name: str) -> str:
    """Rename a file. Extension preserved if not provided in new_name."""
    path = resolve_target_path(target)
    if not path or not os.path.exists(path):
        return f"❌ File not found: '{target}'"

    sys_root = os.environ.get("SystemRoot", "C:\\Windows")
    if path.startswith(sys_root) or "ProgramData" in path:
        return "❌ Safety block: cannot rename system files."

    try:
        ext        = os.path.splitext(path)[1]
        final_name = (f"{new_name}{ext}"
                      if ext and not new_name.lower().endswith(ext.lower())
                      else new_name)
        new_path   = os.path.join(os.path.dirname(path), final_name)

        if os.path.exists(new_path):
            return f"❌ '{final_name}' already exists in the same folder."

        os.rename(path, new_path)
        file_index.remove(path)
        file_index.add(new_path)
        return f"✅ Renamed '{os.path.basename(path)}' → '{final_name}'"

    except PermissionError:
        return "❌ Permission denied. Try running as Admin."
    except Exception as e:
        return f"❌ Rename failed: {e}"


def move_file(target: str, destination: str) -> str:
    """Move a file. Destination supports folder aliases (music, desktop, etc.)."""
    path = resolve_target_path(target)
    if not path or not os.path.exists(path):
        return f"❌ File not found: '{target}'"

    dest = USER_FOLDERS.get(destination.lower().strip(), destination)
    dest = _expand_alias(dest)
    
    # If dest is not an absolute path and doesn't exist, try resolving it as a known folder
    if not os.path.isabs(dest) and not os.path.exists(dest):
        resolved_dest = resolve_target_path(destination)
        if resolved_dest and os.path.isdir(resolved_dest):
            dest = resolved_dest

    try:
        os.makedirs(dest, exist_ok=True)
        filename = os.path.basename(path)
        final_path = os.path.join(dest, filename)
        
        if os.path.exists(final_path):
            return f"❌ Destination file already exists: '{final_path}'"
            
        shutil.move(path, final_path)
        
        # Validation
        if not os.path.exists(final_path):
             return f"❌ Move operation failed silently. File not found at '{final_path}'"
             
        file_index.remove(path)
        file_index.add(final_path)
        return f"✅ Moved '{filename}' → '{dest}'"
    except PermissionError:
        return f"❌ Permission denied moving '{target}'."
    except Exception as e:
        return f"❌ Move failed: {e}"


def copy_file(target: str, destination: str) -> str:
    """Copy a file. Destination supports folder aliases."""
    path = resolve_target_path(target)
    if not path or not os.path.exists(path):
        return f"❌ File not found: '{target}'"

    dest = USER_FOLDERS.get(destination.lower().strip(), destination)
    dest = _expand_alias(dest)

    # Resolution for copy destination too
    if not os.path.isabs(dest) and not os.path.exists(dest):
        resolved_dest = resolve_target_path(destination)
        if resolved_dest and os.path.isdir(resolved_dest):
            dest = resolved_dest

    try:
        os.makedirs(dest, exist_ok=True)
        filename = os.path.basename(path)
        final_path = os.path.join(dest, filename)
        
        if os.path.exists(final_path):
            return f"❌ Destination file already exists: '{final_path}'"
            
        shutil.copy2(path, final_path)
        
        # Validation
        if not os.path.exists(final_path):
             return f"❌ Copy operation failed silently. File not found at '{final_path}'"
             
        file_index.add(final_path)
        return f"✅ Copied '{filename}' → '{dest}'"
    except PermissionError:
        return f"❌ Permission denied copying '{target}'."
    except Exception as e:
        return f"❌ Copy failed: {e}"


def delete_file(target: str) -> str:
    """Delete a single file (folders blocked for safety)."""
    path = resolve_target_path(target)
    if not path or not os.path.exists(path):
        return f"❌ File not found: '{target}'"

    if os.path.isdir(path):
        return f"❌ Safety block: '{target}' is a folder. Only files can be deleted."

    sys_roots = [
        os.environ.get("SystemRoot",        "C:\\Windows"),
        os.environ.get("ProgramFiles",      "C:\\Program Files"),
        os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"),
    ]
    if any(path.startswith(r) for r in sys_roots if r):
        return "❌ Safety block: cannot delete system files."

    try:
        os.remove(path)
        file_index.remove(path)
        return f"✅ Deleted: '{os.path.basename(path)}'"
    except PermissionError:
        return f"❌ Permission denied deleting '{target}'."
    except Exception as e:
        return f"❌ Delete failed: {e}"


def delete_folder(target: str) -> str:
    """Delete a folder and all its contents (shutil.rmtree)."""
    path = resolve_target_path(target)
    if not path or not os.path.exists(path):
        return f"❌ Folder not found: '{target}'"

    if not os.path.isdir(path):
        return f"❌ '{target}' is a file, not a folder. Use delete_file instead."

    sys_roots = [
        os.environ.get("SystemRoot",        "C:\\Windows"),
        os.environ.get("ProgramFiles",      "C:\\Program Files"),
        os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"),
        USERPROFILE  # Prevent deleting the entire user profile
    ]
    if any(path.lower() == r.lower() for r in sys_roots if r):
        return "❌ Safety block: cannot delete base system or profile folders."

    try:
        shutil.rmtree(path)
        file_index.remove(path)
        return f"✅ Deleted folder and contents: '{os.path.basename(path)}'"
    except PermissionError:
        return f"❌ Permission denied deleting folder '{target}'."
    except Exception as e:
        return f"❌ Delete folder failed: {e}"


def list_files(directory: str, extension: str = "") -> str:
    """List files in a directory. Supports folder name aliases."""
    dir_path = USER_FOLDERS.get(directory.lower().strip(), _expand_alias(directory))

    if not os.path.exists(dir_path):
        return f"❌ Directory not found: '{directory}'"

    try:
        files = [
            f for f in os.listdir(dir_path)
            if not extension or f.lower().endswith(extension.lower())
        ]
        if not files:
            return f"📁 '{directory}' is empty."
        file_list = "\n".join(f"  • {f}" for f in sorted(files)[:50])
        return f"📁 Files in '{directory}' ({len(files)} total):\n{file_list}"
    except PermissionError:
        return f"❌ Permission denied accessing '{directory}'."
    except Exception as e:
        return f"❌ List failed: {e}"


def create_folder(folder_name: str, location: str = ".") -> str:
    """Create a new folder at the specified location."""
    base_dir = USER_FOLDERS.get(location.lower().strip(), _expand_alias(location))
    
    if not os.path.exists(base_dir):
        try:
            os.makedirs(base_dir, exist_ok=True)
        except Exception as e:
            return f"❌ Could not create base directory '{base_dir}': {e}"

    new_path = os.path.join(base_dir, folder_name)
    
    if os.path.exists(new_path):
        return f"⚠️ Folder '{folder_name}' already exists at '{base_dir}'"
        
    try:
        os.makedirs(new_path, exist_ok=True)
        file_index.add(new_path)
        return f"✅ Created folder: '{new_path}'"
    except Exception as e:
        return f"❌ Failed to create folder: {e}"


def create_file(file_name: str, location: str = ".", content: str = "") -> str:
    """Create a new text file with optional content."""
    base_dir = USER_FOLDERS.get(location.lower().strip(), _expand_alias(location))
    
    if not os.path.exists(base_dir):
        try:
            os.makedirs(base_dir, exist_ok=True)
        except Exception as e:
            return f"❌ Could not create base directory '{base_dir}': {e}"

    new_path = os.path.join(base_dir, file_name)
    
    try:
        with open(new_path, "w", encoding="utf-8") as f:
            f.write(content)
        file_index.add(new_path)
        return f"✅ Created file: '{new_path}'"
    except Exception as e:
        return f"❌ Failed to create file: {e}"


def get_item_info(target: str) -> str:
    """Get metadata about a file or folder."""
    path = resolve_target_path(target)
    if not path or not os.path.exists(path):
        return f"❌ Not found: '{target}'"
        
    try:
        stats = os.stat(path)
        is_dir = os.path.isdir(path)
        size = stats.st_size
        modified = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stats.st_mtime))
        
        type_str = "Folder" if is_dir else "File"
        size_str = f"{size} bytes" if size < 1024 else f"{size/1024:.1f} KB" if size < 1024*1024 else f"{size/(1024*1024):.1f} MB"
        
        info = [
            f"📍 Path: {path}",
            f"🏷️ Type: {type_str}",
            f"⚖️ Size: {size_str}",
            f"🕒 Modified: {modified}"
        ]
        
        if is_dir:
            try:
                items = os.listdir(path)
                info.append(f"📦 Contains: {len(items)} items")
            except:
                pass
                
        return "\n".join(info)
    except Exception as e:
        return f"❌ Failed to get info: {e}"
