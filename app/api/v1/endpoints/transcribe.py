from fastapi import APIRouter, File, UploadFile, Depends

from app.api import deps
from app.db.models import User
from app.core.config import settings
from app.core.file_utils import (
    ALLOWED_AUDIO_EXTENSIONS,
    ALLOWED_MEDIA_EXTENSIONS,
    ALLOWED_VIDEO_EXTENSIONS,
    build_storage_name,
    save_upload_file,
    validate_extension,
)
from app.schemas.ai import TranscriptionResponse
from app.services.language_service import language_service
from app.engine.transcribe import transcribe_engine

router = APIRouter()


@router.post("/speech-to-text", response_model=TranscriptionResponse)
async def speech_to_text(
    file: UploadFile = File(...),
    current_user: User = Depends(deps.get_current_user)
):
    suffix = validate_extension(file, ALLOWED_AUDIO_EXTENSIONS)
    stored_name = build_storage_name(file.filename)
    stored_path = settings.UPLOAD_DIR / stored_name
    save_upload_file(file, stored_path)

    payload = transcribe_engine.transcribe(stored_path)
    payload["media_url"] = f"/media/{stored_name}"
    payload["media_kind"] = "video" if suffix in ALLOWED_VIDEO_EXTENSIONS else "audio"
    payload["full_text_vi"] = language_service.translate_text(payload["full_text_ja"], "ja", "vi")
    payload["analysis"] = language_service.analyze_text(payload["full_text_ja"])
    for segment in payload["segments"]:
        segment["text_vi"] = language_service.translate_text(segment["text_ja"], "ja", "vi")
    return TranscriptionResponse.model_validate(payload)


@router.post("/media-to-text", response_model=TranscriptionResponse)
async def media_to_text(
    file: UploadFile = File(...),
    current_user: User = Depends(deps.get_current_user)
):
    suffix = validate_extension(file, ALLOWED_MEDIA_EXTENSIONS)
    stored_name = build_storage_name(file.filename)
    stored_path = settings.UPLOAD_DIR / stored_name
    save_upload_file(file, stored_path)

    payload = transcribe_engine.transcribe(stored_path)
    payload["media_url"] = f"/media/{stored_name}"
    payload["media_kind"] = "video" if suffix in ALLOWED_VIDEO_EXTENSIONS else "audio"
    payload["full_text_vi"] = language_service.translate_text(payload["full_text_ja"], "ja", "vi")
    payload["analysis"] = language_service.analyze_text(payload["full_text_ja"])
    for segment in payload["segments"]:
        segment["text_vi"] = language_service.translate_text(segment["text_ja"], "ja", "vi")
    return TranscriptionResponse.model_validate(payload)
