"""
Test Wake Word Detection
Simple test of Picovoice Porcupine integration.
"""

import sys
import os
sys.path.append(os.path.join(os.getcwd(), "backend"))

from dotenv import load_dotenv
load_dotenv()

print("="*70)
print("WAKE WORD DETECTION TEST")
print("="*70)

# Check environment
print("\n📋 Configuration:")
access_key = os.getenv("PICOVOICE_ACCESS_KEY")
wake_word = os.getenv("WAKE_WORD", "jarvis")

if access_key:
    print(f"✅ PICOVOICE_ACCESS_KEY: {access_key[:10]}...")
else:
    print("❌ PICOVOICE_ACCESS_KEY not set")
    print("   Get free key from: https://console.picovoice.ai/")
    print("   Add to .env: PICOVOICE_ACCESS_KEY=your_key")

print(f"⚡ Wake word: '{wake_word}'")

# Test import
print("\n📦 Testing imports...")
try:
    from capabilities.wake_word import WakeWordDetector, listen_for_wake_word
    print("✅ wake_word module imported")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

# Test initialization
print("\n🔧 Testing initialization...")
try:
    detector = WakeWordDetector(wake_word=wake_word)
    if detector.porcupine:
        print("✅ WakeWordDetector initialized successfully")
    else:
        print("⚠️  Detector created but Porcupine not initialized")
        print("   This is expected if PICOVOICE_ACCESS_KEY is missing")
except Exception as e:
    print(f"❌ Initialization error: {e}")
    import traceback
    traceback.print_exc()

# Test listening (if initialized)
if access_key:
    print(f"\n🎧 Starting wake word detection test...")
    print(f"   Say '{wake_word}' to test")
    print("   Press Ctrl+C to stop")
    
    def callback():
        print("\n🎉 SUCCESS! Wake word detected!")
        print("   Callback triggered correctly")
    
    try:
        listen_for_wake_word(wake_word=wake_word, callback=callback, sensitivity=0.5)
    except Exception as e:
        print(f"\n❌ Error: {e}")
else:
    print("\n⚠️  Skipping detection test (no API key)")
    print("   Set PICOVOICE_ACCESS_KEY to test actual detection")

print("\n" + "="*70)
print("WAKE WORD TEST COMPLETE")
print("="*70)
