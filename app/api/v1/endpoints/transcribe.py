from fastapi import APIRouter, File, UploadFile, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session

from app.api import deps
from app.core.config import settings
from app.core.file_utils import (
    ALLOWED_AUDIO_EXTENSIONS,
    ALLOWED_MEDIA_EXTENSIONS,
    ALLOWED_VIDEO_EXTENSIONS,
    build_storage_name,
    save_upload_file,
    validate_extension,
)
from app.db.models import MediaTranscriptHistory
from app.schemas.ai import MediaTranscriptHistoryResponse, TranscriptionResponse
from app.engine.transcribe import transcribe_engine
from app.services.language_service import language_service

router = APIRouter()


class YouTubeTranscriptionRequest(BaseModel):
    url: HttpUrl


def _map_transcription_error(exc: Exception) -> HTTPException:
    detail = str(exc).strip() or exc.__class__.__name__
    lowered = detail.lower()
    if any(token in lowered for token in ("invalid data found when processing input", "could not decode", "moov atom not found", "end of file")):
        return HTTPException(status_code=400, detail=f"Invalid or corrupted media file: {detail}")
    return HTTPException(status_code=500, detail=f"Transcription failed: {detail}")


def _store_transcription_history(
    db: Session,
    *,
    title: str,
    source_type: str,
    source_uri: str | None,
    payload: dict,
    media_url: str | None,
    media_kind: str | None,
    owner_user_id=None,
) -> None:
    serialized_segments = jsonable_encoder(payload.get("segments") or [])
    entry = MediaTranscriptHistory(
        owner_user_id=getattr(owner_user_id, "user_id", None),
        title=title,
        source_type=source_type,
        source_uri=source_uri,
        media_url=media_url,
        media_kind=media_kind,
        duration=payload.get("duration") or 0.0,
        full_text_ja=payload.get("full_text_ja") or "",
        full_text_vi=payload.get("full_text_vi"),
        segments=serialized_segments,
    )
    db.add(entry)
    db.commit()


def _build_media_title(filename: str | None) -> str:
    if not filename:
        return "Untitled media"
    name = filename.rsplit("/", 1)[-1]
    return name.rsplit(".", 1)[0] if "." in name else name


def _enrich_history_segments(segments: list[dict] | None) -> list[dict]:
    enriched: list[dict] = []
    for raw_segment in segments or []:
        segment = dict(raw_segment)
        segment_text = language_service.extract_japanese_text(segment.get("text_ja") or "")
        if segment_text:
            segment_display = language_service.build_text_display(segment_text, include_translation=True)
            segment["text_ja"] = segment_text
            segment["text_vi"] = segment.get("text_vi") or segment_display.translation_vi
            segment["text_display"] = segment.get("text_display") or segment_display

        words = []
        for raw_word in segment.get("words") or []:
            word = dict(raw_word)
            word_text = language_service.extract_japanese_text(word.get("text_ja") or "")
            if word_text:
                word["text_ja"] = word_text
                word["text_display"] = word.get("text_display") or language_service.build_text_display(
                    word_text,
                    include_translation=True,
                )
            words.append(word)
        segment["words"] = words
        enriched.append(segment)
    return enriched


@router.post("/speech-to-text", response_model=TranscriptionResponse)
async def speech_to_text(
    file: UploadFile = File(...),
    db: Session = Depends(deps.get_db),
    _current_user = Depends(deps.get_optional_user)
):
    suffix = validate_extension(file, ALLOWED_AUDIO_EXTENSIONS)
    stored_name = build_storage_name(file.filename)
    stored_path = settings.UPLOAD_DIR / stored_name
    save_upload_file(file, stored_path)
    media_kind = "video" if suffix in ALLOWED_VIDEO_EXTENSIONS else "audio"
    try:
        audio_source = transcribe_engine.prepare_audio_source(stored_path, media_kind)
        payload = transcribe_engine.transcribe(audio_source)
    except Exception as exc:
        raise _map_transcription_error(exc) from exc
    payload["media_url"] = f"/media/{stored_name}"
    payload["media_kind"] = media_kind
    payload["media_title"] = _build_media_title(file.filename)
    _store_transcription_history(
        db,
        title=payload["media_title"],
        source_type=media_kind,
        source_uri=file.filename,
        payload=payload,
        media_url=payload["media_url"],
        media_kind=payload["media_kind"],
        owner_user_id=_current_user,
    )
    return TranscriptionResponse.model_validate(payload)


@router.post("/media-to-text", response_model=TranscriptionResponse)
async def media_to_text(
    file: UploadFile = File(...),
    db: Session = Depends(deps.get_db),
    _current_user = Depends(deps.get_optional_user)
):
    suffix = validate_extension(file, ALLOWED_MEDIA_EXTENSIONS)
    stored_name = build_storage_name(file.filename)
    stored_path = settings.UPLOAD_DIR / stored_name
    save_upload_file(file, stored_path)
    media_kind = "video" if suffix in ALLOWED_VIDEO_EXTENSIONS else "audio"
    try:
        audio_source = transcribe_engine.prepare_audio_source(stored_path, media_kind)
        payload = transcribe_engine.transcribe(audio_source)
    except Exception as exc:
        raise _map_transcription_error(exc) from exc
    payload["media_url"] = f"/media/{stored_name}"
    payload["media_kind"] = media_kind
    payload["media_title"] = _build_media_title(file.filename)
    _store_transcription_history(
        db,
        title=payload["media_title"],
        source_type=media_kind,
        source_uri=file.filename,
        payload=payload,
        media_url=payload["media_url"],
        media_kind=payload["media_kind"],
        owner_user_id=_current_user,
    )
    return TranscriptionResponse.model_validate(payload)


@router.post("/youtube-to-text", response_model=TranscriptionResponse)
async def youtube_to_text(
    request: YouTubeTranscriptionRequest,
    db: Session = Depends(deps.get_db),
    _current_user = Depends(deps.get_optional_user)
):
    try:
        downloaded_media = transcribe_engine.download_youtube_media(str(request.url))
        audio_source = transcribe_engine.prepare_audio_source(downloaded_media.path, downloaded_media.media_kind)
        payload = transcribe_engine.transcribe(audio_source)
    except Exception as exc:
        mapped = _map_transcription_error(exc)
        raise HTTPException(status_code=mapped.status_code, detail=f"YouTube transcription failed: {mapped.detail}") from exc
    payload["media_url"] = f"/media/{downloaded_media.path.name}"
    payload["media_kind"] = downloaded_media.media_kind
    payload["media_title"] = downloaded_media.title or str(request.url)
    _store_transcription_history(
        db,
        title=payload["media_title"],
        source_type="youtube",
        source_uri=str(request.url),
        payload=payload,
        media_url=payload["media_url"],
        media_kind=payload["media_kind"],
        owner_user_id=_current_user,
    )
    return TranscriptionResponse.model_validate(payload)


@router.get("/history", response_model=list[MediaTranscriptHistoryResponse])
async def get_transcription_history(
    db: Session = Depends(deps.get_db),
    _current_user = Depends(deps.get_optional_user)
):
    items = (
        db.query(MediaTranscriptHistory)
        .order_by(MediaTranscriptHistory.created_at.desc(), MediaTranscriptHistory.history_id.desc())
        .all()
    )
    return [
        MediaTranscriptHistoryResponse(
            history_id=item.history_id,
            title=item.title,
            source_type=item.source_type,
            source_uri=item.source_uri,
            media_url=item.media_url,
            media_kind=item.media_kind,
            duration=item.duration,
            full_text_ja=normalized_text,
            full_text_vi=display.translation_vi if display else item.full_text_vi,
            text_display=display,
            segments=enriched_segments,
            created_at=item.created_at,
        )
        for item in items
        for normalized_text in [language_service.extract_japanese_text(item.full_text_ja or "")]
        for display in [language_service.build_text_display(normalized_text, include_translation=True) if normalized_text else None]
        for enriched_segments in [_enrich_history_segments(item.segments or [])]
    ]
