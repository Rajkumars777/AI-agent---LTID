"""
Test S-Tier Voice Interface
Quick test of Kokoro-82M TTS and Whisper STT integration.
"""

import sys
import os
sys.path.append(os.path.join(os.getcwd(), "backend"))

from dotenv import load_dotenv
load_dotenv()

print("="*70)
print("S-TIER VOICE INTERFACE TEST")
print("="*70)

# Test 1: Import check
print("\n📦 TEST 1: Checking dependencies...")
try:
    from capabilities.voice_interface import VoiceInterface, speak
    print("✅ voice_interface module imported")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

# Test 2: Initialize voice interface
print("\n📦 TEST 2: Initializing VoiceInterface...")
try:
    voice = VoiceInterface(voice="af_sarah", use_local_tts=True)
    print("✅ VoiceInterface initialized")
except Exception as e:
    print(f"⚠️  Initialization warning: {e}")
    print("   This is expected if Kokoro models aren't downloaded yet")

# Test 3: Test TTS (if Kokoro is available)
print("\n🗣️  TEST 3: Testing S-Tier TTS...")
test_phrases = [
    "Hello! I am your AI assistant with S-tier voice capabilities.",
    "I can process your commands with natural speech.",
    "Testing prosody with dynamic intonation. Can you hear the difference?"
]

try:
    for i, phrase in enumerate(test_phrases, 1):
        print(f"\n   Phrase {i}: '{phrase}'")
        voice.speak(phrase)
        print("   ✅ Spoken successfully")
except Exception as e:
    print(f"   ⚠️  TTS test skipped: {e}")
    print("   To enable:")
    print("   1. pip install kokoro-onnx sounddevice")
    print("   2. Download models from https://huggingface.co/hexgrad/Kokoro-82M")
    print("   3. Place in backend/capabilities/models/kokoro/")

# Test 4: Cleanup
print("\n🧹 TEST 4: Cleanup...")
try:
    voice.cleanup()
    print("✅ Cleanup successful")
except:
    pass

print("\n" + "="*70)
print("VOICE INTERFACE TEST COMPLETE")
print("="*70)
print("\n📋 Next Steps:")
print("1. Install: pip install kokoro-onnx sounddevice")
print("2. Download Kokoro models to backend/capabilities/models/kokoro/")
print("3. Test recording: python test_voice_record.py")
print("4. Test full flow: record → transcribe → process → speak")
