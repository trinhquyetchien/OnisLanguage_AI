import shutil
import io
from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, File, UploadFile
from PIL import Image
from app.core.config import settings
from app.schemas.kanji import KanjiResponse
from app.services.kanji_service import kanji_service
from app.api.utils import validate_extension

router = APIRouter()

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}

@router.post("/predict", response_model=KanjiResponse)
async def predict_kanji(file: UploadFile = File(...)):
    validate_extension(file, ALLOWED_IMAGE_EXTENSIONS)

    try:
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data))
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Invalid image file: {e}")

    payload = kanji_service.predict(image)
    return KanjiResponse.model_validate(payload)
