import shutil
from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, File, UploadFile
from app.core.config import settings
from app.schemas.ocr import OCRResponse
from app.services.ocr_service import ocr_service
from app.api.utils import validate_extension

router = APIRouter()

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}

@router.post("/process", response_model=OCRResponse)
async def ocr_image(file: UploadFile = File(...)):
    validate_extension(file, ALLOWED_IMAGE_EXTENSIONS)

    stored_name = f"{uuid4().hex}_{file.filename}"
    stored_path = settings.UPLOAD_DIR / stored_name

    with stored_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    payload = ocr_service.process_image(stored_path)
    payload["image_url"] = f"/media/{stored_name}"
    
    return OCRResponse.model_validate(payload)
