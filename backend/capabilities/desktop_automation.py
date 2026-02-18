"""
desktop_automation.py
=====================
Visual RPA engine for desktop control.
Handles Start Menu search, click, type, scroll, screenshot operations.
"""

import os
import asyncio
import time
import base64
from io import BytesIO
from typing import Optional, Tuple

import pyautogui
import pyperclip
from capabilities.vision_engine import vision_engine

# ─────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────

# Configurable via env var — increase on slower systems
RPA_PAUSE       = float(os.environ.get("RPA_PAUSE", "0.15"))
START_MENU_WAIT = 0.8    # seconds to wait after typing in Start Menu
WIN_ACTIVATE_WAIT = 0.5  # seconds to wait after activating a window

# Safety: move mouse to top-left corner to abort
pyautogui.FAILSAFE = True
pyautogui.PAUSE    = RPA_PAUSE


# ─────────────────────────────────────────────────────
# DESKTOP AUTOMATION ENGINE
# ─────────────────────────────────────────────────────

class DesktopAutomation:
    """
    Visual RPA engine. Controls the desktop via mouse, keyboard,
    and window management. Used as Stage 5 (last resort) in the
    resolve_target_path chain and for browser interaction.
    """

    def __init__(self):
        self.last_window_title: Optional[str] = None

    # ─────────────────────────────────────
    # START MENU
    # ─────────────────────────────────────

    def search_start_menu(self, query: str, action: str = "open") -> str:
        """
        Visually searches Windows Start Menu and performs an action.

        Flow:
          1. Press Win key
          2. Paste query (reliable for special chars/spaces)
          3. Wait 0.8s for UI latency
          4. Verify via pygetwindow
          5. Press Enter as fallback if window not detected

        Args:
            query:  App or file name to search
            action: "open" (default) → press Enter
                    "click"          → OCR click on result
                    "find"           → just search, no launch
        """
        import pygetwindow as gw

        try:
            print(f"[RPA] Searching Start Menu for '{query}'...")

            # Step 1: Open Start Menu
            pyautogui.press("win")
            time.sleep(0.5)

            # Step 2: Paste query (more reliable than write for spaces/specials)
            pyperclip.copy(query)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(START_MENU_WAIT)

            # Step 3: Verify via window title
            windows = gw.getWindowsWithTitle(query)
            window_found = bool(windows)

            if window_found:
                print(f"[RPA] ✅ Window '{query}' detected in taskbar")

            # Step 4: Execute action
            if action.lower() == "open":
                pyautogui.press("enter")   # launch top result
                time.sleep(0.5)
                status = "opened via Enter" if not window_found else "window already appeared"
                return f"✅ Start Menu: '{query}' {status}"

            elif action.lower() == "click":
                result = self.click_text(query, fuzzy=True, retries=2)
                return result

            elif action.lower() == "find":
                if window_found:
                    return f"✅ Found '{query}' in Start Menu"
                return f"⚠️ '{query}' searched but not confirmed in taskbar"

            return f"✅ Start Menu search for '{query}' completed"

        except Exception as e:
            return f"❌ Start Menu error for '{query}': {e}"

    async def search_start_menu_async(self, query: str, action: str = "open") -> str:
        """Async wrapper — runs sync search in thread pool to avoid blocking event loop."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.search_start_menu, query, action
        )

    # ─────────────────────────────────────
    # CLICK
    # ─────────────────────────────────────

    def click_text(
        self,
        text:         str,
        double_click: bool = False,
        fuzzy:        bool = True,
        retries:      int  = 3,
        window_title: Optional[str] = None
    ) -> str:
        """
        Finds text on screen via OCR and clicks it.
        Retries if not found immediately (UI may still be loading).
        """
        import pygetwindow as gw

        # Use remembered window if none provided
        if not window_title and self.last_window_title:
            window_title = self.last_window_title
            print(f"[RPA] Using remembered window: '{window_title}'")

        for attempt in range(retries):
            print(f"[RPA] Click attempt {attempt + 1}/{retries} for '{text}'...")

            region = self._get_window_region(window_title)

            coords = vision_engine.find_text_center(text, fuzzy=fuzzy, region=region)
            if coords:
                x, y = coords
                self._move_and_click(x, y, double_click)
                return f"✅ Clicked '{text}' at ({x}, {y})"

            if attempt < retries - 1:
                time.sleep(1.5)   # wait for UI to load

        return f"❌ Could not find text '{text}' after {retries} attempts"

    def click_icon(
        self,
        icon_path:    str,
        double_click: bool = False,
        window_title: Optional[str] = None
    ) -> str:
        """Finds an icon image on screen and clicks it."""
        region = self._get_window_region(window_title)

        coords = vision_engine.find_image_center(icon_path, region=region)
        if coords:
            x, y = coords
            self._move_and_click(x, y, double_click)
            return f"✅ Clicked icon '{os.path.basename(icon_path)}' at ({x}, {y})"

        return f"❌ Icon not found: '{icon_path}'"

    def click_coords(self, x: int, y: int, double_click: bool = False) -> str:
        """Click at specific pixel coordinates."""
        try:
            self._move_and_click(x, y, double_click)
            return f"✅ Clicked at ({x}, {y})"
        except Exception as e:
            return f"❌ Click failed at ({x}, {y}): {e}"

    def right_click(self, x: int, y: int) -> str:
        """Right-click at specific coordinates."""
        try:
            pyautogui.moveTo(x, y, duration=0.1)
            pyautogui.rightClick()
            return f"✅ Right-clicked at ({x}, {y})"
        except Exception as e:
            return f"❌ Right-click failed: {e}"

    # ─────────────────────────────────────
    # TYPE
    # ─────────────────────────────────────

    def type_text(
        self,
        text:         str,
        window_title: Optional[str] = None,
        use_paste:    bool = True
    ) -> str:
        """
        Types text into focused window.
        Uses clipboard paste by default — reliable for special chars, unicode, spaces.

        Args:
            text:         Text to type
            window_title: Optional window to focus first
            use_paste:    True = ctrl+v (reliable), False = pyautogui.write (slower)
        """
        # Retry logic for finding the window
        found = False
        for i in range(5):
            if not window_title and self.last_window_title:
                window_title = self.last_window_title
            
            if window_title:
                if self._focus_window(window_title):
                    found = True
                    break
                print(f"[RPA] Waiting for window '{window_title}'... ({i+1}/5)")
                time.sleep(1.0)
            else:
                # No title provided, use currently active window
                found = True
                break
        
        if not found and window_title:
            return f"❌ Could not focus window '{window_title}' for typing."

        try:
            if use_paste:
                # Most reliable method — works with all characters
                pyperclip.copy(text)
                pyautogui.hotkey("ctrl", "v")
            else:
                # Fallback: character by character (slower but no clipboard side effects)
                pyautogui.write(text, interval=0.08)

            return f"✅ Typed: '{text}'"
        except Exception as e:
            return f"❌ Type failed: {e}"

    # ─────────────────────────────────────
    # KEYBOARD
    # ─────────────────────────────────────

    def press_key(self, key: str) -> str:
        """Press a single key (enter, esc, tab, delete, etc.)"""
        try:
            pyautogui.press(key)
            return f"✅ Pressed: '{key}'"
        except Exception as e:
            return f"❌ Key press failed '{key}': {e}"

    def hotkey(self, *keys: str) -> str:
        """Press a key combination (e.g. ctrl+c, alt+f4)"""
        try:
            pyautogui.hotkey(*keys)
            combo = "+".join(keys)
            return f"✅ Hotkey: '{combo}'"
        except Exception as e:
            return f"❌ Hotkey failed: {e}"

    # ─────────────────────────────────────
    # SCROLL
    # ─────────────────────────────────────

    def scroll(self, clicks: int, x: int = None, y: int = None) -> str:
        """
        Scroll mouse wheel.
        Positive = scroll up, Negative = scroll down.
        Optional x,y to scroll at specific position.
        """
        try:
            if x is not None and y is not None:
                pyautogui.scroll(clicks, x=x, y=y)
            else:
                pyautogui.scroll(clicks)
            direction = "up" if clicks > 0 else "down"
            return f"✅ Scrolled {direction} ({abs(clicks)} clicks)"
        except Exception as e:
            return f"❌ Scroll failed: {e}"

    # ─────────────────────────────────────
    # DRAG & DROP
    # ─────────────────────────────────────

    def drag_and_drop(
        self,
        src_x: int, src_y: int,
        dst_x: int, dst_y: int,
        duration: float = 0.5
    ) -> str:
        """Drag from source coordinates to destination coordinates."""
        try:
            pyautogui.moveTo(src_x, src_y, duration=0.1)
            pyautogui.dragTo(dst_x, dst_y, duration=duration, button="left")
            return f"✅ Dragged ({src_x},{src_y}) → ({dst_x},{dst_y})"
        except Exception as e:
            return f"❌ Drag failed: {e}"

    # ─────────────────────────────────────
    # SCREENSHOT
    # ─────────────────────────────────────

    def capture_screenshot(self, region: Optional[Tuple] = None) -> str:
        """
        Captures the screen and returns a base64-encoded PNG string.
        Used for: browser streaming, visual verification, debugging.

        Args:
            region: Optional (left, top, width, height) tuple
        Returns:
            Base64 PNG string
        """
        try:
            screenshot = pyautogui.screenshot(region=region)
            buffer = BytesIO()
            screenshot.save(buffer, format="PNG")
            return base64.b64encode(buffer.getvalue()).decode("utf-8")
        except Exception as e:
            print(f"[RPA] Screenshot failed: {e}")
            return ""

    def get_screen_size(self) -> Tuple[int, int]:
        """Returns (width, height) of the screen."""
        return pyautogui.size()

    # ─────────────────────────────────────
    # WINDOW MANAGEMENT
    # ─────────────────────────────────────

    def focus_window(self, title: str) -> str:
        """Focus a window by title."""
        result = self._focus_window(title)
        if result:
            return f"✅ Focused window: '{title}'"
        return f"❌ Window not found: '{title}'"

    def get_active_window(self) -> Optional[str]:
        """Returns the title of the currently active window."""
        try:
            import pygetwindow as gw
            win = gw.getActiveWindow()
            return win.title if win else None
        except Exception:
            return None

    # ─────────────────────────────────────
    # PRIVATE HELPERS
    # ─────────────────────────────────────

    def _get_window_region(
        self,
        window_title: Optional[str]
    ) -> Optional[Tuple[int, int, int, int]]:
        """
        Returns (left, top, width, height) of a window.
        Activates and restores minimized windows.
        Returns None if window not found.
        """
        if not window_title:
            return None

        try:
            import pygetwindow as gw

            # Get all candidate windows
            candidates = gw.getWindowsWithTitle(window_title)
            
            # Filter for visible windows only (if possible)
            visible_candidates = [w for w in candidates if hasattr(w, 'visible') and w.visible]
            if not visible_candidates:
                visible_candidates = candidates # Fallback to all if visible property fails or none found
                
            # Priority 1: Exact match (case-insensitive)
            wins = [
                w for w in visible_candidates
                if w.title.lower() == window_title.lower()
            ]
            
            # Priority 2: Ends with match (handles "(1) WhatsApp")
            if not wins:
                wins = [
                    w for w in visible_candidates
                    if w.title.lower().endswith(window_title.lower())
                ]

            # Priority 3: Substring match (fallback)
            if not wins:
                wins = visible_candidates

            if not wins:
                print(f"[RPA] Window '{window_title}' not found")
                return None

            win = wins[0]
            self.last_window_title = win.title  # remember for next call

            try:
                if win.isMinimized:
                    win.restore()
                win.activate()
                time.sleep(WIN_ACTIVATE_WAIT)
            except Exception:
                pass

            return (win.left, win.top, win.width, win.height)

        except Exception as e:
            print(f"[RPA] Window region error: {e}")
            return None

    def _focus_window(self, window_title: str) -> bool:
        """Focus a window. Returns True if successful."""
        region = self._get_window_region(window_title)
        return region is not None

    def _move_and_click(self, x: int, y: int, double: bool = False):
        """Move mouse to coordinates and click."""
        pyautogui.moveTo(x, y, duration=0.1)
        if double:
            pyautogui.doubleClick()
        else:
            pyautogui.click()


# ─────────────────────────────────────────────────────
# GLOBAL INSTANCE
# ─────────────────────────────────────────────────────

desktop_agent = DesktopAutomation()
