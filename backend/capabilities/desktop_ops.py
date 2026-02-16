"""
Desktop Operations Capability
==============================
Handles OPEN, CLOSE, DELETE, RENAME, MOVE actions for Windows.

OPEN uses a multi-strategy approach:
  1. PowerShell Get-StartApps (finds ALL apps including UWP/Store apps)
  2. Registry App Paths lookup
  3. Start Menu shortcut (.lnk) scan
  4. Common install directories scan
  5. Shell 'start' command fallback
"""

import os
import re
import shutil
import subprocess
import winreg
from typing import Optional


# ── Strategy 1: PowerShell Get-StartApps (MOST RELIABLE) ──
def _find_via_start_apps(app_name: str) -> Optional[str]:
    """
    Uses PowerShell Get-StartApps to find apps by name.
    Returns the AppID which can be launched via explorer.exe shell:AppsFolder\\{AppID}
    Uses -EncodedCommand to avoid $_ escaping issues.
    """
    try:
        import base64
        # Build the PowerShell script
        ps_script = f'Get-StartApps | Where-Object {{$_.Name -like "*{app_name}*"}} | Select-Object -First 1 -ExpandProperty AppID'
        # Encode as UTF-16LE base64 (required by -EncodedCommand)
        encoded = base64.b64encode(ps_script.encode('utf-16-le')).decode('ascii')
        
        result = subprocess.run(
            ["powershell", "-NoProfile", "-EncodedCommand", encoded],
            capture_output=True, text=True, timeout=15
        )
        app_id = result.stdout.strip()
        if app_id and len(app_id) > 2 and "not recognized" not in app_id:
            print(f"[DesktopOps] Found via Get-StartApps: {app_id}", flush=True)
            return app_id
    except Exception as e:
        print(f"[DesktopOps] Get-StartApps failed: {e}", flush=True)
    return None


# ── Strategy 2: Registry App Paths ──
def _find_in_registry(app_name: str) -> Optional[str]:
    """Check HKLM\\...\\App Paths for registered executables."""
    app_lower = app_name.lower()
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths") as key:
            i = 0
            while True:
                try:
                    name = winreg.EnumKey(key, i)
                    if app_lower in name.lower():
                        with winreg.OpenKey(key, name) as subkey:
                            path, _ = winreg.QueryValueEx(subkey, "")
                            if os.path.exists(path):
                                print(f"[DesktopOps] Found in registry: {path}", flush=True)
                                return path
                    i += 1
                except OSError:
                    break
    except Exception:
        pass
    return None


# ── Strategy 3: Start Menu Shortcut Scan ──
def _find_in_start_menu(app_name: str) -> Optional[str]:
    """Scan Start Menu folders for .lnk shortcuts matching the app name."""
    app_lower = app_name.lower()
    start_menu_paths = []

    for env_var in ["ProgramData", "AppData", "LocalAppData"]:
        base = os.environ.get(env_var, "")
        if base:
            start_menu_paths.append(
                os.path.join(base, r"Microsoft\Windows\Start Menu\Programs")
            )

    for root_path in start_menu_paths:
        if not os.path.isdir(root_path):
            continue
        for root, dirs, files in os.walk(root_path):
            for f in files:
                if f.lower().endswith(".lnk") and app_lower in f.lower():
                    full = os.path.join(root, f)
                    print(f"[DesktopOps] Found shortcut: {full}", flush=True)
                    return full
    return None


# ── Strategy 4: Common Install Directories ──
def _find_in_install_dirs(app_name: str) -> Optional[str]:
    """Search common installation paths for matching .exe files."""
    app_lower = app_name.lower()
    search_dirs = [
        os.environ.get("ProgramFiles", r"C:\Program Files"),
        os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
        os.path.join(os.environ.get("LocalAppData", ""), "Programs"),
        os.environ.get("LocalAppData", ""),
    ]

    for base_dir in search_dirs:
        if not base_dir or not os.path.isdir(base_dir):
            continue
        # Only search 2 levels deep to avoid being too slow
        for entry in os.listdir(base_dir):
            entry_path = os.path.join(base_dir, entry)
            if app_lower in entry.lower() and os.path.isdir(entry_path):
                # Look for .exe inside this folder
                for sub in os.listdir(entry_path):
                    if sub.lower().endswith(".exe") and app_lower in sub.lower():
                        full = os.path.join(entry_path, sub)
                        print(f"[DesktopOps] Found exe: {full}", flush=True)
                        return full
    return None


# ════════════════════════════════════════════════════════════
#  PUBLIC API
# ════════════════════════════════════════════════════════════

def open_application(target: str) -> str:
    """
    Opens a file, folder, or application using multiple Windows strategies.
    """
    try:
        print(f"[DesktopOps] Opening: {target}", flush=True)

        # ── If it's a file/folder that exists, open directly ──
        if os.path.exists(target):
            os.startfile(target)
            return f"✅ Opened: {target}"

        # ── If it's a URL ──
        if target.startswith("http") or target.startswith("www."):
            import webbrowser
            url = target if target.startswith("http") else "https://" + target
            webbrowser.open(url)
            return f"✅ Opened URL: {url}"

        # ── Strategy 1: PowerShell Get-StartApps (best for UWP/Store apps) ──
        app_id = _find_via_start_apps(target)
        if app_id:
            subprocess.Popen(
                ["explorer.exe", f"shell:AppsFolder\\{app_id}"],
                shell=False
            )
            return f"✅ Launched '{target}' via Start Menu"

        # ── Strategy 2: Registry lookup ──
        reg_path = _find_in_registry(target)
        if reg_path:
            os.startfile(reg_path)
            return f"✅ Launched '{target}' from registry"

        # ── Strategy 3: Start Menu shortcuts ──
        lnk_path = _find_in_start_menu(target)
        if lnk_path:
            os.startfile(lnk_path)
            return f"✅ Launched '{target}' via Start Menu shortcut"

        # ── Strategy 4: Common install directories ──
        exe_path = _find_in_install_dirs(target)
        if exe_path:
            os.startfile(exe_path)
            return f"✅ Launched '{target}' from install directory"

        # ── Strategy 5: Shell 'start' command (for apps in PATH) ──
        try:
            subprocess.Popen(f"start {target}", shell=True)
            return f"⚠️ Attempted to launch '{target}' via shell command"
        except Exception:
            pass

        return f"❌ Could not find '{target}'. Not found in Start Menu, Registry, or install directories."

    except Exception as e:
        return f"❌ Error opening '{target}': {str(e)}"


def close_application(target: str) -> str:
    """Closes an application by process name."""
    try:
        app_name = target.strip()
        # Add .exe if missing
        exe_name = app_name if app_name.endswith(".exe") else f"{app_name}.exe"

        result = subprocess.run(
            ["taskkill", "/IM", exe_name, "/F"],
            capture_output=True, text=True
        )

        if result.returncode == 0:
            return f"✅ Closed {exe_name}"

        # Try without .exe
        result2 = subprocess.run(
            ["taskkill", "/IM", app_name, "/F"],
            capture_output=True, text=True
        )
        if result2.returncode == 0:
            return f"✅ Closed {app_name}"

        # Try finding the process by window title
        result3 = subprocess.run(
            ["taskkill", "/FI", f"WINDOWTITLE eq {app_name}*", "/F"],
            capture_output=True, text=True
        )
        if result3.returncode == 0:
            return f"✅ Closed window: {app_name}"

        return f"❌ '{app_name}' not found running. Tried: {exe_name}, {app_name}, window title."

    except Exception as e:
        return f"❌ Error closing '{target}': {str(e)}"


def delete_file(target: str) -> str:
    """Deletes a file or directory."""
    try:
        if not os.path.exists(target):
            return f"❌ File not found: {target}"

        if os.path.isfile(target):
            os.remove(target)
            return f"✅ Deleted file: {target}"
        elif os.path.isdir(target):
            shutil.rmtree(target)
            return f"✅ Deleted folder: {target}"

        return f"❌ Could not delete: {target}"
    except Exception as e:
        return f"❌ Error deleting '{target}': {str(e)}"


def rename_file(target: str, new_name: str) -> str:
    """Renames a file or directory."""
    try:
        if not new_name:
            return f"❌ No new name provided for rename."
        if not os.path.exists(target):
            return f"❌ File not found: {target}"

        if os.sep not in new_name and "/" not in new_name:
            directory = os.path.dirname(target)
            new_path = os.path.join(directory, new_name)
        else:
            new_path = new_name

        os.rename(target, new_path)
        return f"✅ Renamed '{os.path.basename(target)}' → '{os.path.basename(new_path)}'"
    except Exception as e:
        return f"❌ Error renaming '{target}': {str(e)}"


def move_file(target: str, destination: str) -> str:
    """Moves a file or directory."""
    try:
        if not destination:
            return f"❌ No destination provided for move."
        if not os.path.exists(target):
            return f"❌ File not found: {target}"

        shutil.move(target, destination)
        return f"✅ Moved '{os.path.basename(target)}' → '{destination}'"
    except Exception as e:
        return f"❌ Error moving '{target}': {str(e)}"
