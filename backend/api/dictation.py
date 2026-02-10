"""
Voice Dictation API - Local & Free
Uses Faster-Whisper for transcription (no cloud API needed).
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
import shutil
import os
import tempfile

router = APIRouter(prefix="/api/voice", tags=["voice"])


@router.post("/transcribe")
async def transcribe_voice(file: UploadFile = File(...)):
    """
    Transcribe audio to text (locally, no API key needed).
    
    The text is returned to the FRONTEND to display in the input box.
    The user then verifies/edits and presses Enter to execute.
    
    Args:
        file: Audio file (WAV or MP3)
        
    Returns:
        {"text": "transcribed text here"}
    """
    temp_path = None
    
    try:
        # Import here to avoid loading model if endpoint not used
        from capabilities.dictation import transcribe_audio
        
        # Save uploaded audio to temporary file
        temp_path = os.path.join(tempfile.gettempdir(), "voice_command.wav")
        
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        print(f"🎤 Received audio file: {file.filename}")
        
        # Transcribe using Faster-Whisper (local)
        text = transcribe_audio(temp_path)
        
        if not text:
            return {"text": "", "error": "No speech detected"}
        
        return {
            "text": text,
            "success": True,
            "method": "faster-whisper (local)"
        }
        
    except Exception as e:
        print(f"❌ Transcription error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {str(e)}"
        )
        
    finally:
        # Clean up temp file
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
