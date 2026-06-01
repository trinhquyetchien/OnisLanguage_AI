from fastapi import APIRouter, File, UploadFile, Depends

from app.api import deps
from app.core.config import settings
from app.core.file_utils import ALLOWED_IMAGE_EXTENSIONS, build_storage_name, save_upload_file, validate_extension
from app.schemas.ai import OCRResponse
from app.engine.ocr import ocr_engine
from app.services.language_service import language_service

router = APIRouter()


@router.post("/image-to-text", response_model=OCRResponse)
async def image_to_text(
    file: UploadFile = File(...),
    _current_user = Depends(deps.get_optional_user)
):
    validate_extension(file, ALLOWED_IMAGE_EXTENSIONS)

    stored_name = build_storage_name(file.filename)
    stored_path = settings.UPLOAD_DIR / stored_name
    save_upload_file(file, stored_path)

    payload = ocr_engine.process_image(stored_path)
    normalized_text = language_service.extract_japanese_text(payload.get("full_text") or "")
    if normalized_text:
        payload["full_text"] = normalized_text
        payload["translated_text_vi"] = language_service.translate_text(normalized_text, "ja", "vi")
        payload["text_display"] = language_service.build_text_display(normalized_text, include_translation=True)
        payload["sentences"] = language_service.build_sentence_displays(normalized_text)
        payload["analysis"] = language_service.build_fast_analysis(normalized_text)
    payload["image_url"] = f"/media/{stored_name}"
    return OCRResponse.model_validate(payload)
