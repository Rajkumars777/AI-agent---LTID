import os
from fastapi import APIRouter, File, UploadFile, HTTPException
from pydantic import BaseModel
import shutil
import tempfile
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Global variable to hold the model instance if we want to reuse it
whisper_model = None

def get_whisper_model():
    global whisper_model
    if whisper_model is None:
        try:
            from faster_whisper import WhisperModel
            # Load the model. 'base' or 'small' is good for testing.
            logger.info("Loading faster-whisper model (base)...")
            whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
            logger.info("Faster-whisper model loaded successfully.")
        except ImportError:
            logger.error("faster-whisper is not installed.")
            raise HTTPException(status_code=500, detail="faster-whisper library is not installed")
        except Exception as e:
            logger.error(f"Error loading whisper model: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to load whisper model: {e}")
    return whisper_model

class VoiceConfig(BaseModel):
    # Dummy config to satisfy frontend checks
    voice: str = "default"
    rate: int = 100
    volume: int = 100

@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """Transcribe an uploaded audio file using faster-whisper."""
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")

    # Save the uploaded file temporarily
    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, file.filename or "audio.wav")
    
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Load model and transcribe
        model = get_whisper_model()
        
        logger.info(f"Transcribing {temp_file_path}...")
        segments, info = model.transcribe(temp_file_path, beam_size=1) # Reduced beam_size for speed on CPU
        
        text = " ".join([segment.text for segment in segments]).strip()
        logger.info(f"Transcription result: {text}")
        
        return {"text": text}
        
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temporary file
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        except Exception as cleanup_error:
            logger.error(f"Error cleaning up temp directory: {cleanup_error}")

# Dummy endpoints to prevent frontend failing on startup or config
@router.get("/config")
async def get_config():
    return {"status": "ok", "config": {}}

@router.post("/config")
async def set_config(config: VoiceConfig):
    return {"status": "ok", "config": config.dict()}

@router.post("/enable")
async def enable_voice():
    return {"status": "ok"}

@router.post("/disable")
async def disable_voice():
    return {"status": "ok"}

@router.post("/test-tts")
async def test_tts(text: str = "Test"):
    return {"status": "ok", "message": "TTS testing not fully implemented"}
