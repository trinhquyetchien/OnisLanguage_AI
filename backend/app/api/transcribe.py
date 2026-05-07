import shutil
from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, File, UploadFile
from app.core.config import settings
from app.schemas.transcribe import TranscriptionResponse
from app.services.transcription_service import transcription_service
from app.api.utils import validate_extension

router = APIRouter()

ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".mp4", ".flac", ".ogg", ".aac", ".webm", ".mov", ".mkv"}
VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".mkv"}

@router.post("/process", response_model=TranscriptionResponse)
async def transcribe_media(file: UploadFile = File(...)):
    suffix = validate_extension(file, ALLOWED_AUDIO_EXTENSIONS)

    stored_name = f"{uuid4().hex}_{file.filename}"
    stored_path = settings.UPLOAD_DIR / stored_name

    with stored_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    payload = transcription_service.transcribe(stored_path)
    payload["media_url"] = f"/media/{stored_name}"
    payload["media_kind"] = "video" if suffix in VIDEO_EXTENSIONS else "audio"
    
    return TranscriptionResponse.model_validate(payload)
