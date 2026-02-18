"""
desktop_ops.py
==============
Universal File/App Resolver with 5-stage fallback chain.
Handles all file and application operations for the desktop agent.
"""

import os
import re
import shutil
import subprocess
import winreg
import time
import glob
from typing import Optional, List, Dict

# ─────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────

USERPROFILE  = os.environ.get("USERPROFILE", os.path.expanduser("~"))
CACHE_TTL    = 600   # 10 minutes in seconds
MAX_DEPTH    = 3     # max folder depth for cache scan

# All standard Windows user folders to scan + alias mapping
USER_FOLDERS: Dict[str, str] = {
    "desktop":   os.path.join(USERPROFILE, "Desktop"),
    "documents": os.path.join(USERPROFILE, "Documents"),
    "downloads": os.path.join(USERPROFILE, "Downloads"),
    "music":     os.path.join(USERPROFILE, "Music"),
    "pictures":  os.path.join(USERPROFILE, "Pictures"),
    "videos":    os.path.join(USERPROFILE, "Videos"),
    "onedrive":  os.path.join(USERPROFILE, "OneDrive"),
}

# Registry keys to search for installed apps
REGISTRY_KEYS = [
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths",
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
    r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
]


# ─────────────────────────────────────────────────────
# STAGE 4: HIGH-SPEED FILE CACHE
# ─────────────────────────────────────────────────────

class FileSearchIndex:
    """
    Singleton file cache. Scans common user folders once every 10 minutes.
    Subsequent searches are near-instant dictionary lookups.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.cache        = {}
            cls._instance.last_rebuild = 0
        return cls._instance

    def _rebuild(self):
        """Scans user folders and builds filename → full path cache."""
        print("[Cache] Rebuilding file index...")
        new_cache = {}
        built     = 0

        for folder_path in USER_FOLDERS.values():
            if not os.path.exists(folder_path):
                continue
            try:
                for root, dirs, files in os.walk(
                    folder_path,
                    onerror=lambda e: None   # skip permission errors silently
                ):
                    # Enforce depth limit for performance
                    depth = root.count(os.sep) - folder_path.count(os.sep)
                    if depth >= MAX_DEPTH:
                        dirs.clear()
                        continue

                    for filename in files:
                        full_path = os.path.join(root, filename)
                        new_cache[filename.lower()] = full_path
                        built += 1

            except Exception as e:
                print(f"[Cache] Skipping '{folder_path}': {e}")

        self.cache        = new_cache
        self.last_rebuild = time.time()
        print(f"[Cache] Index built: {built} files indexed")

    def invalidate(self):
        """Force cache rebuild on next search (call after rename/move/delete)."""
        self.last_rebuild = 0

    def search(self, query: str, strict: bool = False) -> Optional[str]:
        """Search cache for a filename. Rebuilds if stale."""
        if time.time() - self.last_rebuild > CACHE_TTL:
            self._rebuild()

        query_low = query.lower()

        # Exact match (Always returned)
        if query_low in self.cache:
            return self.cache[query_low]

        # Partial match fallback — Priority 1: Executables/Shortcuts/Documents
        priority_exts = (
            # Executables
            ".exe", ".lnk", ".url", ".bat", ".cmd",
            # Documents
            ".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt",
            ".txt", ".md", ".csv", ".json", ".py"
        )
        for name, path in self.cache.items():
            if query_low in name and name.lower().endswith(priority_exts):
                return path

        # If strict mode (used for 'Open' commands), stop here.
        # We don't want 'Open WhatsApp' to pick 'WhatsApp Img.jpg'
        if strict:
            return None

        # Partial match fallback — Priority 2: Any file
        for name, path in self.cache.items():
            if query_low in name:
                return path

        return None


# ─────────────────────────────────────────────────────
# RESOLVER HELPERS
# ─────────────────────────────────────────────────────

def _is_visual_rpa(path: Optional[str]) -> bool:
    """Check if resolve result is a Visual RPA token."""
    return bool(path and path.startswith("VISUAL_RPA:"))

def _get_rpa_target(path: str) -> str:
    """Extract target name from Visual RPA token."""
    return path.replace("VISUAL_RPA:", "")


def _search_start_menu(app_name: str, system: bool = False) -> Optional[str]:
    """
    Stage 2: Scan Start Menu for .lnk shortcuts.
    system=False → User Start Menu (no admin needed)
    system=True  → System Start Menu (read-only safe, blocks write ops)
    """
    app_low = app_name.lower()

    if system:
        bases = [os.environ.get("ProgramData", "")]
    else:
        bases = [
            os.environ.get("AppData", ""),
            USERPROFILE,
        ]

    for base in bases:
        if not base:
            continue
        start_menu_path = os.path.join(
            base, "Microsoft", "Windows", "Start Menu", "Programs"
        )
        if not os.path.exists(start_menu_path):
            continue

        for root, _, files in os.walk(start_menu_path):
            for filename in files:
                if filename.lower().endswith(".lnk") and app_low in filename.lower():
                    return os.path.abspath(os.path.join(root, filename))

    return None


def _search_registry(app_name: str) -> Optional[str]:
    """
    Stage 3: Search Windows Registry for installed application paths.
    Checks App Paths + both 32/64-bit Uninstall keys.
    """
    app_low = app_name.lower()

    for reg_key_path in REGISTRY_KEYS:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_key_path) as key:
                i = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        i += 1

                        if app_low not in subkey_name.lower():
                            continue

                        with winreg.OpenKey(key, subkey_name) as subkey:
                            # Try common value names for exe path
                            for value_name in ("", "InstallLocation", "DisplayIcon"):
                                try:
                                    path, _ = winreg.QueryValueEx(subkey, value_name)
                                    # Clean up path (remove quotes, args)
                                    path = path.strip().strip('"').split('"')[0].split(',')[0].strip()
                                    if path and os.path.exists(path):
                                        return path
                                except Exception:
                                    continue

                    except OSError:
                        break  # no more subkeys

        except Exception:
            continue  # key doesn't exist or no access

    return None


def _search_uwp_apps(app_name: str) -> Optional[str]:
    """
    Stage 2.5: Search for UWP/Store Apps via PowerShell.
    Returns 'shell:AppsFolder\\<AppID>' which can be passed to os.startfile.
    """
    try:
        # Simplified one-liner to get the AppID directly
        cmd = [
            "powershell", "-NoProfile", "-Command",
            f"(Get-StartApps | Where-Object {{ $_.Name -like '*{app_name}*' }} | Select-Object -First 1).AppID"
        ]
        # Use subprocess to capture output without opening a window
        result = subprocess.run(cmd, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        
        app_id = result.stdout.strip()
        if app_id:
            return f"shell:AppsFolder\\{app_id}"
            
    except Exception as e:
        print(f"[DesktopOps] UWP Search Error: {e}")
    
    return None


def _visual_fallback(target: str) -> Optional[str]:
    """
    Stage 5: Last resort — Visual RPA via Start Menu UI.
    Returns a VISUAL_RPA token; caller is responsible for triggering automation.
    """
    try:
        from capabilities.desktop_automation import desktop_agent  # noqa
        print(f"[DesktopOps] Stage 5: Visual RPA token issued for '{target}'")
        return f"VISUAL_RPA:{target}"
    except ImportError:
        print("[DesktopOps] Stage 5: desktop_automation not available")
        return None


# ─────────────────────────────────────────────────────
# PUBLIC RESOLVER — 5-STAGE CHAIN
# ─────────────────────────────────────────────────────

def resolve_target_path(target: str) -> Optional[str]:
    """
    Resolves any file name, app name, or path to an absolute path.

    5-Stage fallback chain:
      1. Direct path      — os.path.exists()
      2. Start Menu .lnk  — User first (no admin), then System
      3. Registry         — App Paths + Uninstall keys
      4. File Cache       — 10-minute indexed scan of user folders
      5. Visual RPA       — Trigger Start Menu UI search (last resort)

    Returns:
      - Absolute path string on success
      - "VISUAL_RPA:<target>" token if only visual search can help
      - None if all stages fail
    """
    if not target or not target.strip():
        return None

    target = target.strip()

    # ── Stage 1: Direct path ──
    if os.path.exists(target):
        print(f"[Resolver] Stage 1 hit: {target}")
        return os.path.abspath(target)

    # ── Stage 2: Start Menu — User (no admin needed) ──
    path = _search_start_menu(target, system=False)
    if path:
        print(f"[Resolver] Stage 2 (User Start Menu) hit: {path}")
        return path

    # ── Stage 2b: Start Menu — System (read-only safe) ──
    path = _search_start_menu(target, system=True)
    if path:
        print(f"[Resolver] Stage 2 (System Start Menu) hit: {path}")
        return path

    # ── Stage 2.5: UWP / Store Apps ──
    path = _search_uwp_apps(target)
    if path:
        print(f"[Resolver] Stage 2.5 (UWP) hit: {path}")
        return path

    # ── Stage 3: Registry ──
    path = _search_registry(target)
    if path:
        print(f"[Resolver] Stage 3 (Registry) hit: {path}")
        return path

    # ── Stage 4: File Cache ──
    # Strict search first (Exact match OR Executables/Docs)
    path = FileSearchIndex().search(target, strict=True)
    if path:
        print(f"[Resolver] Stage 4 (Cache - Strict) hit: {path}")
        return path
    
    # If target was a full path (e.g. hallucinated by LLM) and failed, try basename
    if os.sep in target:
        basename = os.path.basename(target)
        print(f"[Resolver] Retrying cache with basename: '{basename}'")
        path = FileSearchIndex().search(basename, strict=True)
        if path:
            print(f"[Resolver] Stage 4 (Cache - Basename Strict) hit: {path}")
            return path

    # ── Stage 4.5: Loose Cache Fallback? ──
    # No, we intentionally skip loose partial matches (e.g. "whatsapp" matching "whatsapp image.jpg")
    # to allow Visual RPA (Stage 5) to handle the app launch.
    # If the user really meant the image, they should be more specific or use 'find' command.

    # ── Stage 5: Visual RPA ──

    # ── Stage 5: Visual RPA ──
    print(f"[Resolver] All stages exhausted. Falling back to Visual RPA.")
    return _visual_fallback(target)


# ─────────────────────────────────────────────────────
# ACTIONS
# ─────────────────────────────────────────────────────

def open_application(target: str) -> str:
    """Open a file or application by name or path."""
    path = resolve_target_path(target)

    if not path:
        return f"❌ Could not find '{target}' anywhere."

    # Visual RPA fallback
    if _is_visual_rpa(path):
        try:
            from capabilities.desktop_automation import desktop_agent
            return desktop_agent.search_start_menu(_get_rpa_target(path))
        except Exception as e:
            return f"❌ Visual RPA failed for '{target}': {e}"

    try:
        os.startfile(path)
        return f"✅ Opened: {os.path.basename(path)}"
    except Exception as e:
        return f"❌ Error opening '{path}': {e}"


def rename_file(target: str, new_name: str) -> str:
    """Rename a file or user-level shortcut."""
    path = resolve_target_path(target)

    if not path:
        return f"❌ File not found: '{target}'"

    if _is_visual_rpa(path):
        return f"❌ Cannot rename '{target}' — file not found on disk."

    # Safety: Block system-level shortcuts (requires admin)
    if "ProgramData" in path:
        return (
            f"❌ Safety block: '{target}' is a system shortcut in ProgramData. "
            f"Renaming system shortcuts requires Admin rights."
        )

    try:
        dir_name = os.path.dirname(path)
        ext      = os.path.splitext(path)[1]

        # Preserve original extension if not provided in new_name
        if not new_name.lower().endswith(ext.lower()):
            final_name = f"{new_name}{ext}"
        else:
            final_name = new_name

        new_path = os.path.join(dir_name, final_name)

        if os.path.exists(new_path):
            return f"❌ A file named '{final_name}' already exists."

        os.rename(path, new_path)
        FileSearchIndex().invalidate()   # force cache refresh
        return f"✅ Renamed '{os.path.basename(path)}' → '{final_name}'"

    except PermissionError:
        return f"❌ Permission denied renaming '{target}'. Try running as Admin."
    except Exception as e:
        return f"❌ Rename failed: {e}"


def move_file(target: str, destination: str) -> str:
    """Move a file to a destination folder. Supports folder name aliases."""
    path = resolve_target_path(target)

    if not path:
        return f"❌ File not found: '{target}'"

    if _is_visual_rpa(path):
        return f"❌ Cannot move '{target}' — file not found on disk."

    # Resolve destination alias (e.g. "music" → full path)
    dest_path = USER_FOLDERS.get(destination.lower().strip(), destination)

    if not os.path.exists(dest_path):
        try:
            os.makedirs(dest_path, exist_ok=True)
            print(f"[DesktopOps] Created destination folder: {dest_path}")
        except Exception as e:
            return f"❌ Destination folder not found and could not be created: {e}"

    try:
        final_dest = shutil.move(path, dest_path)
        FileSearchIndex().invalidate()   # force cache refresh
        return f"✅ Moved '{os.path.basename(path)}' → '{dest_path}'"
    except PermissionError:
        return f"❌ Permission denied moving '{target}'."
    except Exception as e:
        return f"❌ Move failed: {e}"


def delete_file(target: str) -> str:
    """
    Delete a single file only.
    Folder deletion is blocked for safety — must be explicit.
    """
    path = resolve_target_path(target)

    if not path or not os.path.exists(path):
        return f"❌ File not found: '{target}'"

    if _is_visual_rpa(path):
        return f"❌ Cannot delete '{target}' — file not found on disk."

    # Safety: Block folder deletion
    if os.path.isdir(path):
        return (
            f"❌ Safety block: '{target}' is a folder. "
            f"Folder deletion is disabled for safety. Please specify a file."
        )

    # Safety: Block system paths
    system_paths = [
        os.environ.get("SystemRoot", "C:\\Windows"),
        os.environ.get("ProgramFiles", "C:\\Program Files"),
        os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"),
    ]
    if any(path.startswith(sp) for sp in system_paths if sp):
        return f"❌ Safety block: Cannot delete system files."

    try:
        os.remove(path)
        FileSearchIndex().invalidate()
        return f"✅ Deleted: '{os.path.basename(path)}'"
    except PermissionError:
        return f"❌ Permission denied deleting '{target}'."
    except Exception as e:
        return f"❌ Delete failed: {e}"


def copy_file(target: str, destination: str) -> str:
    """Copy a file to a destination folder. Supports folder name aliases."""
    path = resolve_target_path(target)

    if not path:
        return f"❌ File not found: '{target}'"

    if _is_visual_rpa(path):
        return f"❌ Cannot copy '{target}' — file not found on disk."

    dest_path = USER_FOLDERS.get(destination.lower().strip(), destination)

    try:
        os.makedirs(dest_path, exist_ok=True)
        shutil.copy2(path, dest_path)
        return f"✅ Copied '{os.path.basename(path)}' → '{dest_path}'"
    except PermissionError:
        return f"❌ Permission denied copying '{target}'."
    except Exception as e:
        return f"❌ Copy failed: {e}"


def list_files(directory: str, extension: str = "") -> str:
    """List files in a directory. Supports folder name aliases."""
    dir_path = USER_FOLDERS.get(directory.lower().strip(), directory)

    if not os.path.exists(dir_path):
        return f"❌ Directory not found: '{directory}'"

    try:
        files = [
            f for f in os.listdir(dir_path)
            if not extension or f.lower().endswith(extension.lower())
        ]
        if not files:
            return f"📁 '{directory}' is empty."

        file_list = "\n".join(f"  • {f}" for f in sorted(files)[:30])
        return f"📁 Files in '{directory}' ({len(files)} total):\n{file_list}"

    except PermissionError:
        return f"❌ Permission denied accessing '{directory}'."
    except Exception as e:
        return f"❌ List failed: {e}"
