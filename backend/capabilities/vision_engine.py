
import os
import cv2
import numpy as np
import pyautogui
import pytesseract
from PIL import Image
from typing import Tuple, Optional, List, Dict, Any

# Configure pytesseract path for Windows
# We prioritize a BUNDLED versions for portability
backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
project_root = os.path.dirname(backend_root)

possible_tesseract_paths = [
    # 1. Bundled in backend/bin (Portable for PyInstaller)
    os.path.join(backend_root, "bin", "tesseract", "tesseract.exe"),
    # 2. Bundled in src-tauri/binaries (Portable for Tauri)
    os.path.join(project_root, "frontend", "src-tauri", "binaries", "tesseract", "tesseract.exe"),
    # 3. System installation
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.getenv("TESSERACT_PATH", "tesseract")
]

# Try to find tesseract
tesseract_cmd = "tesseract"
for path in possible_tesseract_paths:
    if os.path.exists(path):
        tesseract_cmd = path
        print(f"✅ Found Tesseract at: {tesseract_cmd}")
        break

pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

class VisionEngine:
    def __init__(self):
        try:
            self.screen_width, self.screen_height = pyautogui.size()
        except:
            self.screen_width, self.screen_height = 1920, 1080 # Fallback

    def capture_screen(self, region: Optional[Tuple[int, int, int, int]] = None):
        """
        Captures a screenshot of the entire screen or a specific region.
        region: (left, top, width, height)
        """
        try:
            screenshot = pyautogui.screenshot(region=region)
            return screenshot
        except Exception as e:
            print(f"Error capturing screen: {e}")
            return None

    def find_text_center(self, target_text: str, fuzzy: bool = True, region: Optional[Tuple[int, int, int, int]] = None) -> Optional[Tuple[int, int]]:
        """
        Finds the center coordinates of the specified text on the screen using OCR.
        If region is provided, search is restricted to that area.
        Returns absolute (x, y) screen coordinates or None if not found.
        """
        screenshot = self.capture_screen(region=region)
        if not screenshot: return None
        
        offset_x, offset_y = (region[0], region[1]) if region else (0, 0)

        # Diagnostic: Save screenshot
        debug_path = os.path.join(os.getcwd(), "debug_vision_last.png")
        try:
            screenshot.save(debug_path)
        except:
            pass

        try:
            # Check if tesseract is available
            pytesseract.get_tesseract_version()
            # PSM 11: Sparse text. Find as much text as possible in no particular order.
            data = pytesseract.image_to_data(screenshot, config='--psm 11', output_type=pytesseract.Output.DICT)
        except pytesseract.TesseractNotFoundError:
            print("❌ VISUAL RPA ERROR: Tesseract-OCR not found on system.")
            return None
        
        target = target_text.lower().strip()
        n_boxes = len(data['text'])
        
        # Pass 1: Exact matches
        for i in range(n_boxes):
            found_text = data['text'][i].lower().strip()
            if not found_text: continue
            
            if target == found_text:
                try:
                    conf = int(data['conf'][i])
                except:
                    conf = 0
                if conf > 30:
                    (lx, ly, lw, lh) = (data['left'][i], data['top'][i], data['width'][i], data['height'][i])
                    # Add offset of the region to get absolute screen coords
                    return (offset_x + lx + lw // 2, offset_y + ly + lh // 2)

        # Pass 2: Fuzzy/Partial matches
        import re
        for i in range(n_boxes):
            found_text = data['text'][i].lower().strip()
            if not found_text: continue
            
            match = False
            if fuzzy:
                pattern = rf"\b{re.escape(target)}\b"
                if re.search(pattern, found_text):
                    match = True
                elif target in found_text:
                    match = True
            
            try:
                conf = int(data['conf'][i])
            except:
                conf = 0

            if match and conf > 30: 
                (lx, ly, lw, lh) = (data['left'][i], data['top'][i], data['width'][i], data['height'][i])
                abs_x, abs_y = offset_x + lx + lw // 2, offset_y + ly + lh // 2
                print(f"DEBUG VISION: Found '{found_text}' at relative ({lx},{ly}), absolute ({abs_x},{abs_y})")
                return (abs_x, abs_y)
        
        if region:
            print(f"DEBUG VISION: Text '{target}' NOT FOUND in specified region {region}.")
        else:
            print(f"DEBUG VISION: Text '{target}' NOT FOUND on full screen.")
        return None

    def find_image_center(self, template_path: str, threshold: float = 0.8, region: Optional[Tuple[int, int, int, int]] = None) -> Optional[Tuple[int, int]]:
        """
        Finds the center coordinates of a template image on the screen using OpenCV.
        """
        if not os.path.exists(template_path): return None

        screenshot = self.capture_screen(region=region)
        if not screenshot: return None
        
        offset_x, offset_y = (region[0], region[1]) if region else (0, 0)

        screenshot_np = np.array(screenshot)
        screenshot_cv = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)
        screenshot_gray = cv2.cvtColor(screenshot_cv, cv2.COLOR_BGR2GRAY)
        
        template = cv2.imread(template_path, 0)
        if template is None: return None

        w, h = template.shape[::-1]
        res = cv2.matchTemplate(screenshot_gray, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

        if max_val >= threshold:
            center_x = offset_x + max_loc[0] + w // 2
            center_y = offset_y + max_loc[1] + h // 2
            return (center_x, center_y)
        
        return None

    def read_screen_text(self, region: Optional[Tuple[int, int, int, int]] = None) -> str:
        """
        Reads all text from the screen or a region.
        """
        screenshot = self.capture_screen(region)
        if not screenshot: return ""
        try:
            text = pytesseract.image_to_string(screenshot)
            return text.strip()
        except:
            return ""

vision_engine = VisionEngine()
