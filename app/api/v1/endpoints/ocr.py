from fastapi import APIRouter, File, UploadFile, Depends

from app.api import deps
from app.db.models import User
from app.core.config import settings
from app.core.file_utils import ALLOWED_IMAGE_EXTENSIONS, build_storage_name, save_upload_file, validate_extension
from app.schemas.ai import OCRResponse
from app.services.language_service import language_service
from app.engine.ocr import ocr_engine

router = APIRouter()


@router.post("/image-to-text", response_model=OCRResponse)
async def image_to_text(
    file: UploadFile = File(...),
    current_user: User = Depends(deps.get_current_user)
):
    validate_extension(file, ALLOWED_IMAGE_EXTENSIONS)

    stored_name = build_storage_name(file.filename)
    stored_path = settings.UPLOAD_DIR / stored_name
    save_upload_file(file, stored_path)

    payload = ocr_engine.process_image(stored_path)
    payload["image_url"] = f"/media/{stored_name}"
    payload["translated_text_vi"] = language_service.translate_text(payload["full_text"], "ja", "vi")
    payload["analysis"] = language_service.analyze_text(payload["full_text"])
    return OCRResponse.model_validate(payload)
