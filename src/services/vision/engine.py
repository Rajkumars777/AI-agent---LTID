"""
src/services/vision/engine.py
==============================
Complete vision system with dual OCR engines and SmartLocator.
- Primary: Tesseract (fast, English-optimized)
- Backup: EasyOCR (slower, better for mixed languages)
- SmartLocator: Finds UI elements by text, not pixel coordinates
"""

import os
import re
import time
from typing import Optional, Tuple, List, Dict
from pathlib import Path

import pytesseract
import cv2
import numpy as np
from PIL import Image, ImageGrab

# Optional: EasyOCR (backup engine)
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    print("[Vision] EasyOCR not available - fallback disabled")

# ─────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────

# Tesseract path (Windows)
if os.name == 'nt':
    tesseract_path = os.environ.get(
        'TESSERACT_PATH',
        r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    )
    if os.path.exists(tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        print(f"✅ Found Tesseract at: {tesseract_path}")
    else:
        print(f"⚠️ Tesseract not found at: {tesseract_path}")


class VisionEngine:
    """
    Complete vision system for desktop automation.
    
    Features:
    - SmartLocator: Find elements by text (OCR-based)
    - Template matching: Find elements by image
    - Dual OCR: Tesseract (fast) + EasyOCR (accurate)
    - Image preprocessing for better OCR
    """
    
    def __init__(self):
        self.easyocr_reader = None  # Lazy load
    
    # ══════════════════════════════════════════════════
    # SMARTLOCATOR - TEXT-BASED ELEMENT FINDING
    # ══════════════════════════════════════════════════
    
    def find_text_center(
        self,
        text: str,
        fuzzy: bool = True,
        region: Optional[Tuple[int, int, int, int]] = None,
        use_easyocr: bool = False
    ) -> Optional[Tuple[int, int]]:
        """
        Finds text on screen and returns center coordinates.
        This is SmartLocator - finds elements by reading their text, not coordinates.
        
        Args:
            text: Text to find
            fuzzy: Allow partial matches (e.g., "Login" matches "Login to Account")
            region: (left, top, width, height) to search in specific area
            use_easyocr: Use EasyOCR instead of Tesseract (slower but more accurate)
        
        Returns:
            (x, y) center coordinates or None if not found
        """
        # Capture screen
        screenshot = self._capture_screen(region)
        
        # Preprocess for better OCR
        preprocessed = self._preprocess_for_ocr(screenshot)
        
        # Run OCR
        if use_easyocr and EASYOCR_AVAILABLE:
            ocr_data = self._ocr_with_easyocr(preprocessed)
        else:
            ocr_data = self._ocr_with_tesseract(preprocessed)
        
        # Find matching text
        text_lower = text.lower()
        
        for item in ocr_data:
            detected_text = item['text'].lower()
            
            # Exact or fuzzy match
            if (not fuzzy and detected_text == text_lower) or \
               (fuzzy and text_lower in detected_text):
                # Calculate center
                bbox = item['bbox']
                center_x = (bbox[0] + bbox[2]) // 2
                center_y = (bbox[1] + bbox[3]) // 2
                
                # Adjust for region offset
                if region:
                    center_x += region[0]
                    center_y += region[1]
                
                return (center_x, center_y)
        
        return None
    
    def find_all_text_occurrences(
        self,
        text: str,
        region: Optional[Tuple[int, int, int, int]] = None
    ) -> List[Tuple[int, int]]:
        """Finds all occurrences of text and returns all coordinates."""
        screenshot = self._capture_screen(region)
        preprocessed = self._preprocess_for_ocr(screenshot)
        ocr_data = self._ocr_with_tesseract(preprocessed)
        
        results = []
        text_lower = text.lower()
        
        for item in ocr_data:
            if text_lower in item['text'].lower():
                bbox = item['bbox']
                center_x = (bbox[0] + bbox[2]) // 2
                center_y = (bbox[1] + bbox[3]) // 2
                
                if region:
                    center_x += region[0]
                    center_y += region[1]
                
                results.append((center_x, center_y))
        
        return results
    
    # ══════════════════════════════════════════════════
    # WAIT / POLLING HELPERS
    # ══════════════════════════════════════════════════

    def wait_for_text(
        self,
        text: str,
        timeout: float = 15.0,
        poll: float = 0.8,
        region: Optional[Tuple[int, int, int, int]] = None,
        fuzzy: bool = True,
    ) -> bool:
        """
        Polls the screen until `text` appears or timeout is reached.

        Args:
            text:    Text to wait for.
            timeout: Max seconds to wait.
            poll:    Seconds between each check.
            region:  Optional screen region to restrict search.
            fuzzy:   Allow partial matches.

        Returns:
            True if found within timeout, False otherwise.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            coords = self.find_text_center(text, fuzzy=fuzzy, region=region)
            if coords:
                return True
            time.sleep(poll)
        return False

    def find_best_match(
        self,
        text: str,
        template_path: Optional[str] = None,
        region: Optional[Tuple[int, int, int, int]] = None,
        confidence: float = 0.75,
    ) -> Optional[Tuple[int, int, str]]:
        """
        Finds a UI element using the best available method.

        Order:
          1. OCR (Tesseract) — fast, text-based
          2. Template matching (OpenCV) — if template_path is given

        Returns:
            (x, y, method) or None if not found.
            method is one of: 'ocr', 'template'
        """
        # 1. Try OCR
        coords = self.find_text_center(text, fuzzy=True, region=region)
        if coords:
            return (coords[0], coords[1], 'ocr')

        # 2. Try template matching
        if template_path and os.path.exists(template_path):
            coords = self.find_image_center(template_path, confidence=confidence, region=region)
            if coords:
                return (coords[0], coords[1], 'template')

        return None

    # ══════════════════════════════════════════════════
    # TEMPLATE MATCHING - IMAGE-BASED FINDING
    # ══════════════════════════════════════════════════
    
    def find_image_center(
        self,
        template_path: str,
        confidence: float = 0.8,
        region: Optional[Tuple[int, int, int, int]] = None
    ) -> Optional[Tuple[int, int]]:
        """
        Finds image on screen using template matching.
        
        Args:
            template_path: Path to template image (PNG/JPG)
            confidence: Match threshold (0.0 to 1.0)
            region: Search in specific area
        
        Returns:
            (x, y) center coordinates or None
        """
        # Load template
        template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
        if template is None:
            print(f"[Vision] Template not found: {template_path}")
            return None
        
        # Capture screen
        screenshot = self._capture_screen(region)
        screen_gray = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)
        
        # Template matching
        result = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        if max_val >= confidence:
            h, w = template.shape
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            
            if region:
                center_x += region[0]
                center_y += region[1]
            
            return (center_x, center_y)
        
        return None
    
    # ══════════════════════════════════════════════════
    # FULL SCREEN OCR
    # ══════════════════════════════════════════════════
    
    def read_screen_text(
        self,
        region: Optional[Tuple[int, int, int, int]] = None,
        use_easyocr: bool = False
    ) -> str:
        """
        Reads all text from screen.
        
        Returns:
            All detected text as a single string
        """
        screenshot = self._capture_screen(region)
        preprocessed = self._preprocess_for_ocr(screenshot)
        
        if use_easyocr and EASYOCR_AVAILABLE:
            ocr_data = self._ocr_with_easyocr(preprocessed)
            text = "\n".join([item['text'] for item in ocr_data])
        else:
            text = pytesseract.image_to_string(preprocessed)
        
        return text.strip()
    
    def extract_table_from_screen(
        self,
        region: Optional[Tuple[int, int, int, int]] = None
    ) -> List[List[str]]:
        """
        Attempts to extract table structure from screen.
        Returns 2D list of cells.
        """
        screenshot = self._capture_screen(region)
        preprocessed = self._preprocess_for_ocr(screenshot)
        
        # Get detailed OCR data
        ocr_data = self._ocr_with_tesseract(preprocessed, detailed=True)
        
        # Group by rows (similar Y coordinates)
        rows = {}
        for item in ocr_data:
            y = item['bbox'][1]
            # Group items within 20 pixels of same row
            row_key = y // 20
            if row_key not in rows:
                rows[row_key] = []
            rows[row_key].append(item)
        
        # Sort each row by X coordinate
        table = []
        for row_key in sorted(rows.keys()):
            row = sorted(rows[row_key], key=lambda x: x['bbox'][0])
            table.append([item['text'] for item in row])
        
        return table
    
    # ══════════════════════════════════════════════════
    # OCR ENGINES
    # ══════════════════════════════════════════════════
    
    def _ocr_with_tesseract(
        self,
        image: Image.Image,
        detailed: bool = False
    ) -> List[Dict]:
        """
        Runs Tesseract OCR.
        
        Returns:
            [{"text": "...", "bbox": [x1, y1, x2, y2]}, ...]
        """
        # Get detailed data
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        
        results = []
        n_boxes = len(data['text'])
        
        for i in range(n_boxes):
            text = data['text'][i].strip()
            if not text:
                continue
            
            x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
            confidence = int(data['conf'][i])
            
            # Filter low confidence
            if confidence < 30:
                continue
            
            results.append({
                'text': text,
                'bbox': [x, y, x + w, y + h],
                'confidence': confidence
            })
        
        return results
    
    def _ocr_with_easyocr(self, image: Image.Image) -> List[Dict]:
        """
        Runs EasyOCR (backup engine for mixed languages).
        
        Returns same format as Tesseract.
        """
        if not self.easyocr_reader:
            # Lazy load EasyOCR (takes a few seconds first time)
            self.easyocr_reader = easyocr.Reader(['en'], gpu=False)
        
        # Convert PIL to numpy array
        img_array = np.array(image)
        
        # Run OCR
        results_raw = self.easyocr_reader.readtext(img_array)
        
        # Convert to standard format
        results = []
        for bbox, text, conf in results_raw:
            # bbox is [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            x1 = int(min(p[0] for p in bbox))
            y1 = int(min(p[1] for p in bbox))
            x2 = int(max(p[0] for p in bbox))
            y2 = int(max(p[1] for p in bbox))
            
            results.append({
                'text': text,
                'bbox': [x1, y1, x2, y2],
                'confidence': int(conf * 100)
            })
        
        return results
    
    # ══════════════════════════════════════════════════
    # IMAGE PREPROCESSING
    # ══════════════════════════════════════════════════
    
    def _preprocess_for_ocr(self, image: Image.Image) -> Image.Image:
        """
        Preprocesses image to improve OCR accuracy.
        
        Steps:
        1. Convert to grayscale
        2. Increase contrast
        3. Denoise
        4. Threshold (binarize)
        """
        # Convert to OpenCV format
        img = np.array(image)
        
        # Grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        
        # Increase contrast using CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        contrast = clahe.apply(gray)
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(contrast)
        
        # Threshold (binarize) - Otsu's method
        _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Convert back to PIL
        return Image.fromarray(binary)
    
    # ══════════════════════════════════════════════════
    # SCREEN CAPTURE
    # ══════════════════════════════════════════════════
    
    def _capture_screen(
        self,
        region: Optional[Tuple[int, int, int, int]] = None
    ) -> Image.Image:
        """
        Captures screen or region.
        
        Args:
            region: (left, top, width, height) or None for full screen
        
        Returns:
            PIL Image
        """
        if region:
            left, top, width, height = region
            bbox = (left, top, left + width, top + height)
            screenshot = ImageGrab.grab(bbox=bbox)
        else:
            screenshot = ImageGrab.grab()
        
        return screenshot
    
    # ══════════════════════════════════════════════════
    # UTILITIES
    # ══════════════════════════════════════════════════
    
    def save_screenshot(
        self,
        path: str,
        region: Optional[Tuple[int, int, int, int]] = None
    ) -> str:
        """Saves screenshot to file."""
        try:
            screenshot = self._capture_screen(region)
            screenshot.save(path)
            return f"✅ Screenshot saved: {path}"
        except Exception as e:
            return f"❌ Screenshot failed: {e}"
    
    def highlight_text_in_screenshot(
        self,
        text: str,
        output_path: str,
        region: Optional[Tuple[int, int, int, int]] = None
    ) -> str:
        """
        Finds text and saves screenshot with red rectangle around it.
        Useful for debugging SmartLocator.
        """
        screenshot = self._capture_screen(region)
        preprocessed = self._preprocess_for_ocr(screenshot)
        ocr_data = self._ocr_with_tesseract(preprocessed)
        
        # Convert to OpenCV format
        img = np.array(screenshot)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        
        text_lower = text.lower()
        found = False
        
        for item in ocr_data:
            if text_lower in item['text'].lower():
                bbox = item['bbox']
                cv2.rectangle(img, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 0, 255), 3)
                found = True
        
        if found:
            cv2.imwrite(output_path, img)
            return f"✅ Highlighted screenshot saved: {output_path}"
        else:
            return f"❌ Text '{text}' not found on screen"


# ─────────────────────────────────────────────────────
# GLOBAL INSTANCE
# ─────────────────────────────────────────────────────

vision_engine = VisionEngine()
