"""
Local Voice Dictation - Faster-Whisper
FREE, LOCAL, and PRIVATE voice-to-text transcription.

Workflow:
1. User clicks mic → speaks
2. Audio sent to this endpoint
3. Faster-Whisper transcribes locally
4. Text returned to input box (NOT executed)
5. User verifies/edits text
6. User presses Enter to execute
"""

from faster_whisper import WhisperModel
import os
import tempfile

# Initialize model once at startup for speed
# 'tiny.en' = fastest (good for commands)
# 'base.en' = better accuracy, slightly slower
# 'small.en' = best accuracy, slower
# compute_type="int8" = fast on CPU without GPU
print("🎧 Loading Faster-Whisper Model (tiny.en)...")
print("   This happens once at startup, then it's fast!")

model = WhisperModel(
    "tiny.en",
    device="cpu",
    compute_type="int8",
    download_root="models/whisper"  # Cache models here
)

print("✅ Whisper model loaded and ready!")


def transcribe_audio(audio_path: str) -> str:
    """
    Transcribe audio file to text using Faster-Whisper.
    
    Args:
        audio_path: Path to audio file (WAV format)
        
    Returns:
        Transcribed text string
    """
    if not os.path.exists(audio_path):
        print(f"❌ Audio file not found: {audio_path}")
        return ""
    
    try:
        # Transcribe with beam search for better accuracy
        segments, info = model.transcribe(
            audio_path,
            beam_size=5,
            language="en",
            condition_on_previous_text=False  # Better for short commands
        )
        
        # Join all segments into one string
        text = " ".join([segment.text for segment in segments]).strip()
        
        print(f"✅ Transcribed: '{text}'")
        return text
        
    except Exception as e:
        print(f"❌ Transcription error: {e}")
        return ""
