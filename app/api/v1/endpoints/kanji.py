import io

from fastapi import APIRouter, File, HTTPException, UploadFile, Depends
from PIL import Image
from fastapi.responses import Response

from app.api import deps
from app.core.file_utils import ALLOWED_IMAGE_EXTENSIONS, validate_extension
from app.schemas.ai import KanjiResponse
from app.engine.kanji import kanji_engine

router = APIRouter()


@router.post("/draw-and-recognize", response_model=KanjiResponse)
async def draw_and_recognize(
    file: UploadFile = File(...),
    _current_user = Depends(deps.get_optional_user)
):
    validate_extension(file, ALLOWED_IMAGE_EXTENSIONS)

    try:
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid image file: {exc}") from exc

    payload = kanji_engine.predict(image)
    return KanjiResponse.model_validate(payload)


@router.get("/svg/{kanji_char}")
async def kanji_svg(
    kanji_char: str
):
    try:
        content = kanji_engine.get_svg_content(kanji_char)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return Response(content=content, media_type="image/svg+xml")
