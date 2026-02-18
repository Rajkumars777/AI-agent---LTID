
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from capabilities.vision_engine import vision_engine
import pytesseract

print("--- OCR Diagnostic ---")
screenshot = vision_engine.capture_screen()
if not screenshot:
    print("FAILED: Could not capture screen.")
    sys.exit(1)

# Test with PSM 11
data = pytesseract.image_to_data(screenshot, config='--psm 11', output_type=pytesseract.Output.DICT)
texts = [t.strip() for t in data['text'] if t.strip()]

print(f"Total elements found: {len(texts)}")
print(f"Elements: {texts[:100]}")

# Check for digits
digits = [t for t in texts if t.isdigit()]
print(f"Digits found: {digits}")

# Save diagnostic screenshot
screenshot.save("diagnostic_screen.png")
print("Diagnostic screenshot saved to diagnostic_screen.png")
