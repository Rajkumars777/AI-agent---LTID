"""
src/services/desktop/automation.py
====================================
Desktop automation engine.
Handles UI interactions: clicking, typing, window management, screenshots.

The heavier file/app open-close logic lives in ops.py.
This module focuses purely on UI-level automation.

Global instances (import these):
    desktop_automation  — full class instance
    desktop_agent       — alias for backward compatibility
"""

import os
import re
import time
import base64
from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

# Directory where auto-learned templates are stored
_TEMPLATES_DIR = Path(__file__).parent.parent.parent / "assets" / "templates"
_TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

import pyautogui
import pygetwindow as gw
import pyperclip
import psutil
# from AppOpener import open as app_open, close as app_close  # Removed redundancy

# Import the new FREE Agent-S implementation
import sys
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))
try:
    from free_agent_s import free_agent_s
    FREE_AGENT_S_AVAILABLE = True
except ImportError:
    FREE_AGENT_S_AVAILABLE = False
    print("[Automation] free_agent_s not available")

try:
    from pywinauto import Desktop as WinDesktop
    PYWINAUTO_AVAILABLE = True
except ImportError:
    PYWINAUTO_AVAILABLE = False
    print("[Automation] pywinauto not available — deep Windows control disabled")


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

pyautogui.FAILSAFE = True
pyautogui.PAUSE    = float(os.environ.get("RPA_PAUSE", "0.15"))


# ─────────────────────────────────────────────────────────────────────────────
# UI ELEMENT CACHE
# ─────────────────────────────────────────────────────────────────────────────

class UICache:
    """Caches (x, y) positions of UI elements by app+label to skip repeat scans."""

    def __init__(self, ttl: int = 3600):
        self._cache:  Dict[str, Tuple[int, int]] = {}
        self._stamps: Dict[str, float]            = {}
        self._ttl    = ttl

    def get(self, app: str, element: str) -> Optional[Tuple[int, int]]:
        key = f"{app.lower()}:{element.lower()}"
        if key in self._cache and time.time() - self._stamps[key] < self._ttl:
            return self._cache[key]
        self._cache.pop(key, None)
        self._stamps.pop(key, None)
        return None

    def set(self, app: str, element: str, coords: Tuple[int, int]):
        key = f"{app.lower()}:{element.lower()}"
        self._cache[key]  = coords
        self._stamps[key] = time.time()

    def invalidate(self, app: str):
        prefix = f"{app.lower()}:"
        for k in list(self._cache):
            if k.startswith(prefix):
                del self._cache[k]
                del self._stamps[k]


# ─────────────────────────────────────────────────────────────────────────────
# MAIN CLASS
# ─────────────────────────────────────────────────────────────────────────────

class DesktopAutomation:
    """
    UI automation engine. Combines multiple detection methods:
      1. UI cache (instant)
      2. pywinauto Windows-native (fast)
      3. Screenshot OCR (Tesseract) — reads text from screen
      4. OpenCV template matching — matches saved image
      Self-learning: saves cropped templates on first OCR hit.
    """

    # ─────────────────────────────────────────────────────────────────────────────
    # GLOBAL SHORTCUT REGISTRY
    # These provide lightning-fast 'Fast Paths' for common apps.
    # ─────────────────────────────────────────────────────────────────────────────
    GLOBAL_SHORTCUTS = {
        "whatsapp": {
            "search": ("ctrl", "f"),
            "new": ("ctrl", "n"),
            "archive": ("ctrl", "e"),
            "mute": ("ctrl", "shift", "m"),
            "delete": ("ctrl", "backspace"),
        },
        "chrome": {
            "address_bar": ("ctrl", "l"),
            "new_tab": ("ctrl", "t"),
            "close_tab": ("ctrl", "w"),
            "find": ("ctrl", "f"),
            "refresh": ("ctrl", "r"),
            "history": ("ctrl", "h"),
            "downloads": ("ctrl", "j"),
            "incognito": ("ctrl", "shift", "n"),
            "search": ("ctrl", "f"),
        },
        "edge": {
            "address_bar": ("ctrl", "l"),
            "new_tab": ("ctrl", "t"),
            "close_tab": ("ctrl", "w"),
            "find": ("ctrl", "f"),
            "search": ("ctrl", "f"),
        },
        "outlook": {
            "new_mail": ("ctrl", "n"),
            "new": ("ctrl", "n"),
            "send": ("ctrl", "enter"),
            "reply": ("ctrl", "r"),
            "search": ("ctrl", "e"),
        },
        "mail": { # Windows Mail
            "new_mail": ("ctrl", "n"),
            "new": ("ctrl", "n"),
            "send": ("ctrl", "enter"),
            "sync": ("f5"),
            "search": ("ctrl", "e"),
        },
        "notepad": {
            "new": ("ctrl", "n"),
            "open": ("ctrl", "o"),
            "save": ("ctrl", "s"),
            "find": ("ctrl", "f"),
            "search": ("ctrl", "f"),
        },
        "system": {
            "search": ("win", "s"),
            "run": ("win", "r"),
            "settings": ("win", "i"),
            "explorer": ("win", "e"),
            "task_manager": ("ctrl", "shift", "esc"),
            "close": ("alt", "f4"),
            "lock": ("win", "l"),
        }
    }

    def get_shortcut(self, app: str, action: str) -> Optional[Tuple[str, ...]]:
        """Get keys for a specific app action."""
        app_low = app.lower()
        # Handle common browser aliases
        if app_low in ("google chrome", "browser"): app_low = "chrome"
        if app_low in ("ms edge", "microsoft edge"): app_low = "edge"
        if app_low in ("windows mail", "outlook express"): app_low = "mail"
        
        return self.GLOBAL_SHORTCUTS.get(app_low, {}).get(action.lower())

    def execute_shortcut(self, app: str, action: str) -> bool:
        """Find and press a shortcut for an app."""
        keys = self.get_shortcut(app, action)
        if keys:
            print(f"[Automation] ⚡ Shortcut Fast Path: {app}.{action} ({'+'.join(keys)})")
            if len(keys) == 1:
                pyautogui.press(keys[0])
            else:
                pyautogui.hotkey(*keys)
            return True
        return False

    def __init__(self):
        self.ui_cache           = UICache()
        self.last_window_title: Optional[str] = None
        self._vision_engine                   = None  # lazy load

    # ── App management ────────────────────────────────────────────────────────

    def open_application(self, app_name: str, wait: float = 2.0) -> str:
        """Open app using robust ops.py logic."""
        from src.services.desktop.ops import open_application as ops_open
        res = ops_open(app_name)
        time.sleep(wait)
        self.last_window_title = app_name
        return res

    def close_application(self, app_name: str) -> str:
        """Close app using robust ops.py logic."""
        from src.services.desktop.ops import close_application as ops_close
        return ops_close(app_name)

    def _force_close(self, title: str) -> str:
        """Fallback force-close (logic now primarily in ops.py)."""
        from src.services.desktop.ops import close_application as ops_close
        return ops_close(title)

    def is_running(self, app_name: str) -> bool:
        """Check if an app process is running."""
        name_lower = app_name.lower()
        for proc in psutil.process_iter(["name"]):
            try:
                if name_lower in proc.info["name"].lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return False

    # ── Window management ─────────────────────────────────────────────────────

    async def wait_for_window_active(self, title: str, timeout: float = 10.0) -> bool:
        """Wait until a window is active and ready for input using OS polling."""
        # S1-Grade: Use pywinauto for deterministic verification
        if PYWINAUTO_AVAILABLE:
            try:
                import re as _re
                title_re = f".*{_re.escape(title)}.*"
                app = WinDesktop(backend="uia")
                from pywinauto.application import Application
                conn = Application(backend="uia").connect(
                    title_re=title_re, timeout=int(timeout)
                )
                win = conn.window(title_re=title_re)
                win.wait("active ready", timeout=int(timeout))
                print(f"[Automation] ✅ OS-verified: '{title}' is active and ready")
                return True
            except Exception as e:
                print(f"[Automation] pywinauto verify failed: {e}, falling back...")

        # Fallback: pygetwindow polling
        deadline = time.time() + timeout
        while time.time() < deadline:
            active = gw.getActiveWindow()
            if active and title.lower() in active.title.lower():
                return True
            await asyncio.sleep(0.5)
        return False

    def focus_window(self, title: str, wait: float = 0.5) -> str:
        """Focuses window by title with persistence and verification."""
        wins = gw.getWindowsWithTitle(title)
        if not wins:
            # Try fuzzy match if exact failed
            all_wins = gw.getAllTitles()
            matches = [t for t in all_wins if title.lower() in t.lower()]
            if matches: wins = gw.getWindowsWithTitle(matches[0])
            
        if not wins:
            return f"❌ Window not found: '{title}'"
            
        win = wins[0]
        try:
            # Increase retry count and patience for slow-loading apps
            for attempt in range(10): 
                try:
                    if win.isMinimized: win.restore()
                    win.activate()
                    time.sleep(1.0) # Patient wait for focus transition
                    active = gw.getActiveWindow()
                    if active and (title.lower() in active.title.lower()):
                        self.last_window_title = win.title
                        return f"✅ Focused: {win.title}"
                except Exception:
                    time.sleep(0.5)
                    continue
            return f"⚠️ Focused attempted but verification failed for: {win.title}"
        except Exception as e:
            return f"❌ Focus failed: {e}"

    def is_window_active(self, title: str) -> bool:
        """Checks if a window with the given title is currently active."""
        active = gw.getActiveWindow()
        if not active: return False
        return title.lower() in active.title.lower()

    def maximize_window(self, title: str) -> str:
        wins = gw.getWindowsWithTitle(title)
        if not wins:
            return f"❌ Window not found: '{title}'"
        wins[0].maximize()
        return f"✅ Maximized: {title}"

    def minimize_window(self, title: str) -> str:
        wins = gw.getWindowsWithTitle(title)
        if not wins:
            return f"❌ Window not found: '{title}'"
        wins[0].minimize()
        return f"✅ Minimized: {title}"

    def resize_window(self, title: str, width: int, height: int) -> str:
        wins = gw.getWindowsWithTitle(title)
        if not wins:
            return f"❌ Window not found: '{title}'"
        wins[0].resizeTo(width, height)
        self.ui_cache.invalidate(title)
        return f"✅ Resized {title} to {width}x{height}"

    def move_window(self, title: str, x: int, y: int) -> str:
        wins = gw.getWindowsWithTitle(title)
        if not wins:
            return f"❌ Window not found: '{title}'"
        wins[0].moveTo(x, y)
        self.ui_cache.invalidate(title)
        return f"✅ Moved {title} to ({x}, {y})"

    def get_all_windows(self) -> List[Dict[str, Any]]:
        return [
            {
                "title":     win.title,
                "position":  (win.left, win.top),
                "size":      (win.width, win.height),
                "minimized": win.isMinimized,
                "maximized": win.isMaximized,
            }
            for win in gw.getAllWindows() if win.title
        ]

    # ── Screenshot-based element finder ───────────────────────────────────────

    def find_element_on_screen(
        self,
        label: str,
        region: Optional[Tuple] = None,
        fuzzy: bool = True,
    ) -> Optional[Tuple[int, int]]:
        """
        Takes a screenshot and uses OCR to find the (x, y) center of a UI
        element by its visible text label.

        This is the core of the dynamic detection system — no hardcoded
        coordinates. Works for any app, any window size.

        Returns (x, y) or None.
        """
        vision = self._get_vision()
        if not vision:
            return None
        return vision.find_text_center(label, fuzzy=fuzzy, region=region)

    # ── Smart clicking ────────────────────────────────────────────────────────

    async def click(
        self,
        target: str,
        window: Optional[str] = None,
        double: bool = False,
        method: Optional[str] = None,  # Force a specific method: 'cache', 'native', 'agent-s', 'ocr'
        **kwargs
    ) -> str:
        """
        Unified high-speed click method. 
        Tries methods in order of speed: Cache -> Native (pywinauto) -> Agent-S (Vision) -> OCR (Fallback).
        """
        app = window or self.last_window_title or "desktop"
        
        # 0. Shortcut Fast Path (New Lightning Tier)
        # Handle common actions like "search", "new mail", etc.
        if target.lower() in ("search", "find", "new mail", "new", "compose", "send"):
            action_map = {
                "search": "search", "find": "search",
                "new mail": "new_mail", "compose": "new_mail", "new": "new",
                "send": "send"
            }
            action = action_map.get(target.lower())
            if action and self.execute_shortcut(app, action):
                return f"✅ Executed '{target}' via shortcut fast-path"

        # 1. Cache (Instant)
        if not method or method == "cache":
            cached = self.ui_cache.get(app, target)
            if cached:
                self._click(cached[0], cached[1], double)
                return f"✅ Clicked '{target}' via cache"

        # 2. Native Windows API (Fast, Precise)
        if (not method or method == "native") and PYWINAUTO_AVAILABLE and window:
            print(f"[Automation] Trying native click for '{target}' in '{window}'...")
            res = self._click_pywinauto(window, target, double)
            if "✅" in res:
                coords = self._extract_coords(res)
                if coords: self.ui_cache.set(app, target, coords)
                return res

        # 3. Intelligent Agent-S (Most Accurate Vision)
        if (not method or method == "agent-s") and FREE_AGENT_S_AVAILABLE:
            print(f"[Automation] Agent-S analyzing screen for '{target}'...")
            # We pass context to help Agent-S
            task = f"Click the {target}"
            if window: task += f" in the {window} window"
            
            result = await free_agent_s.execute_task(task)
            if result.get("success") and "coordinates" in result:
                x, y = result["coordinates"]
                self.ui_cache.set(app, target, (x, y))
                self._click(x, y, double)
                return f"✅ Clicked '{target}' via Agent-S"

        # 4. Traditional OCR (Fallback)
        if not method or method == "ocr":
            vision = self._get_vision()
            if vision:
                region = self._window_region(window)
                coords = vision.find_text_center(target, fuzzy=True, region=region)
                if coords:
                    x, y = coords
                    self.ui_cache.set(app, target, (x, y))
                    self._click(x, y, double)
                    return f"✅ Clicked '{target}' via OCR"

        # 5. Template Matching (Last Resort if template path exists)
        template_path = kwargs.get("template_path")
        if not template_path:
            auto_tpl = str(_TEMPLATES_DIR / f"{target.lower().replace(' ', '_')}.png")
            if os.path.exists(auto_tpl): template_path = auto_tpl

        if template_path:
            vision = self._get_vision()
            if vision:
                region = self._window_region(window)
                coords = vision.find_image_center(template_path, confidence=0.75, region=region)
                if coords:
                    x, y = coords
                    self.ui_cache.set(app, target, (x, y))
                    self._click(x, y, double)
                    return f"✅ Clicked '{target}' via template"

        return f"❌ Could not find '{target}' using any method"

    def smart_click(self, label: str, **kwargs) -> str:
        """Synchronous wrapper for unified click."""
        import asyncio
        try:
            return asyncio.run(self.click(label, **kwargs))
        except RuntimeError:
            # Already in event loop
            import nest_asyncio
            nest_asyncio.apply()
            return asyncio.run(self.click(label, **kwargs))

    def click_element(self, element_text: str, **kwargs) -> str:
        """Alias for unified click."""
        return self.smart_click(element_text, **kwargs)

    def click_text(self, text: str, **kwargs) -> str:
        """Alias for unified click."""
        return self.smart_click(text, **kwargs)

    def wait_for_element(
        self,
        text: str,
        timeout: float = 15.0,
        region: Optional[Tuple] = None,
    ) -> bool:
        """Polled wait for text to appear."""
        vision = self._get_vision()
        if not vision:
            time.sleep(min(timeout, 5))
            return True
        return vision.wait_for_text(text, timeout=timeout, region=region)

    def _click_pywinauto(self, window_title: str, element_text: str, double: bool) -> str:
        """Native Windows accessibility click."""
        try:
            desk = WinDesktop(backend="uia")
            wins = desk.windows(title_re=f".*{window_title}.*")
            if not wins: return "❌ Window not found"
            win = wins[0]
            # Try buttons first, then any control
            for ctrl_type in ("Button", None):
                try:
                    kw = {"title": element_text}
                    if ctrl_type: kw["control_type"] = ctrl_type
                    elem = win.child_window(**kw)
                    if elem.exists():
                        if double: elem.double_click_input()
                        else: elem.click_input()
                        # Extract coords for cache
                        rect = elem.rectangle()
                        cx, cy = (rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2
                        return f"✅ Clicked '{element_text}' via native at ({cx}, {cy})"
                except: continue
            return "❌ Element not found via native"
        except Exception as e:
            return f"❌ Native error: {e}"

    @staticmethod
    def _extract_coords(result_str: str) -> Optional[Tuple[int, int]]:
        """Parses (x, y) from response strings."""
        m = re.search(r'\((\d+),\s*(\d+)\)', result_str)
        return (int(m.group(1)), int(m.group(2))) if m else None

    # ── Keyboard ──────────────────────────────────────────────────────────────

    def type_text(self, text: str, window_title: Optional[str] = None,
                  use_clipboard: bool = True) -> str:
        """Type text. Clipboard method handles unicode and special chars reliably."""
        if window_title:
            self.focus_window(window_title)
        
        # Shortcut Fast Path for clear-then-type pattern
        if text == "SELECT_ALL_DELETE":
            pyautogui.hotkey("ctrl", "a")
            pyautogui.press("backspace")
            return "✅ Cleared field via shortcuts"

        try:
            if use_clipboard:
                pyperclip.copy(text)
                pyautogui.hotkey("ctrl", "v")
            else:
                pyautogui.write(text, interval=0.08)
            return f"✅ Typed: '{text}'"
        except Exception as e:
            return f"❌ Type failed: {e}"

    def press_key(self, key: str) -> str:
        try:
            pyautogui.press(key)
            return f"✅ Pressed: '{key}'"
        except Exception as e:
            return f"❌ Key press failed: {e}"

    def hotkey(self, *keys: str) -> str:
        try:
            pyautogui.hotkey(*keys)
            return f"✅ Hotkey: '{'+'.join(keys)}'"
        except Exception as e:
            return f"❌ Hotkey failed: {e}"

    # ── Mouse ─────────────────────────────────────────────────────────────────

    def click_coords(self, x: int, y: int, double: bool = False) -> str:
        try:
            self._click(x, y, double)
            return f"✅ Clicked at ({x}, {y})"
        except Exception as e:
            return f"❌ Click failed: {e}"

    def right_click(self, x: int, y: int) -> str:
        try:
            pyautogui.moveTo(x, y, duration=0.1)
            pyautogui.rightClick()
            return f"✅ Right-clicked at ({x}, {y})"
        except Exception as e:
            return f"❌ Right-click failed: {e}"

    def scroll(self, clicks: int, x: Optional[int] = None, y: Optional[int] = None) -> str:
        try:
            if x is not None and y is not None:
                pyautogui.scroll(clicks, x=x, y=y)
            else:
                pyautogui.scroll(clicks)
            direction = "up" if clicks > 0 else "down"
            return f"✅ Scrolled {direction} ({abs(clicks)} clicks)"
        except Exception as e:
            return f"❌ Scroll failed: {e}"

    def drag_and_drop(self, sx: int, sy: int, dx: int, dy: int) -> str:
        try:
            pyautogui.moveTo(sx, sy, duration=0.1)
            pyautogui.dragTo(dx, dy, duration=0.5, button="left")
            return f"✅ Dragged ({sx},{sy}) → ({dx},{dy})"
        except Exception as e:
            return f"❌ Drag failed: {e}"

    # ── Screenshots & OCR ─────────────────────────────────────────────────────

    def capture_screenshot(self, region: Optional[Tuple] = None) -> str:
        """Returns base64-encoded PNG string."""
        try:
            screenshot = pyautogui.screenshot(region=region)
            buf = BytesIO()
            screenshot.save(buf, format="PNG")
            return base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception as e:
            print(f"[Automation] Screenshot failed: {e}")
            return ""

    def get_screen_size(self) -> Tuple[int, int]:
        return pyautogui.size()

    def read_screen_text(self, region: Optional[Tuple] = None) -> str:
        vision = self._get_vision()
        if not vision:
            return "❌ Vision engine not available"
        return vision.read_screen_text(region=region)

    # ── Clipboard ─────────────────────────────────────────────────────────────

    def copy_to_clipboard(self, text: str) -> str:
        try:
            pyperclip.copy(text)
            return f"✅ Copied to clipboard"
        except Exception as e:
            return f"❌ Clipboard copy failed: {e}"

    def get_clipboard_text(self) -> str:
        try:
            return pyperclip.paste()
        except Exception as e:
            return f"❌ Clipboard read failed: {e}"

    # ── Start Menu ────────────────────────────────────────────────────────────

    def search_start_menu(self, query: str, action: str = "open") -> str:
        """Search Windows Start Menu and optionally open the first result."""
        try:
            pyautogui.press("win")
            time.sleep(0.6)
            pyperclip.copy(query)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(1.0)
            if action == "open":
                pyautogui.press("enter")
                return f"✅ Opened '{query}' from Start Menu"
            return f"✅ Searched Start Menu for '{query}'"
        except Exception as e:
            return f"❌ Start Menu search failed: {e}"

    async def search_start_menu_async(self, query: str, action: str = "open") -> str:
        """Async wrapper for search_start_menu."""
        import asyncio
        return await asyncio.to_thread(self.search_start_menu, query, action)

    def execute_dynamic_script(self, code: str, params: Optional[Dict] = None) -> str:
        """
        Executes a generated Python script in a controlled namespace.
        Used for JIT automation.

        The namespace provides:
          - desktop: this DesktopAutomation instance
          - pyautogui, pyperclip, gw, time, os, psutil, subprocess
          - wait_for_window: S1-grade OS polling function
        """
        try:
            from src.tools.generator import generator

            # 1. Safety Check
            safe, blocked = generator.is_safe_code(code)
            if not safe:
                return f"[Error] Safety check failed: Blocked pattern '{blocked}' detected."

            # 2. Prepare namespace with S1-grade helpers
            import subprocess as sp

            def wait_for_window(title: str, timeout: float = 15.0) -> bool:
                """S1-grade: poll OS until window is active (sync wrapper)."""
                if PYWINAUTO_AVAILABLE:
                    import re as _re
                    try:
                        from pywinauto.application import Application
                        title_re = f".*{_re.escape(title)}.*"
                        conn = Application(backend="uia").connect(
                            title_re=title_re, timeout=int(timeout)
                        )
                        win = conn.window(title_re=title_re)
                        win.wait("active ready", timeout=int(timeout))
                        print(f"[DynScript] ✅ OS-verified: '{title}' ready")
                        return True
                    except Exception as e:
                        print(f"[DynScript] pywinauto wait failed: {e}")
                # Fallback: pygetwindow
                deadline = time.time() + timeout
                while time.time() < deadline:
                    try:
                        active = gw.getActiveWindow()
                        if active and title.lower() in active.title.lower():
                            return True
                    except Exception:
                        pass
                    time.sleep(0.5)
                return False

            namespace = {
                "pyautogui": pyautogui,
                "gw": gw,
                "pyperclip": pyperclip,
                "time": time,
                "os": os,
                "psutil": psutil,
                "subprocess": sp,
                "desktop": self,
                "params": params or {},
                "wait_for_window": wait_for_window,
            }

            # 3. Execute
            exec(code, namespace)

            # 4. Call the standard execute() function if it exists
            if "execute" in namespace and callable(namespace["execute"]):
                return namespace["execute"](params or {})

            return "[Success] Dynamic script executed (no return value)"

        except Exception as e:
            return f"[Error] Dynamic execution failed: {str(e)}"

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _click(self, x: int, y: int, double: bool = False):
        pyautogui.moveTo(x, y, duration=0.1)
        pyautogui.doubleClick() if double else pyautogui.click()

    def _window_region(self, title: Optional[str]) -> Optional[Tuple]:
        if not title:
            return None
        wins = gw.getWindowsWithTitle(title)
        if not wins:
            return None
        win = wins[0]
        try:
            if win.isMinimized:
                win.restore()
            win.activate()
            time.sleep(0.3)
        except Exception:
            pass
        return (win.left, win.top, win.width, win.height)

    def _get_vision(self):
        if not self._vision_engine:
            try:
                from src.services.vision.engine import vision_engine
                self._vision_engine = vision_engine
            except ImportError:
                pass
        return self._vision_engine


# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL SINGLETONS
# ─────────────────────────────────────────────────────────────────────────────

desktop_automation = DesktopAutomation()
desktop_agent      = desktop_automation    # Backward-compatible alias
