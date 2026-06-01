from fastapi import APIRouter, Depends

from app.api import deps
from app.db.models import User
from app.schemas.language import AnalyzeTextRequest, AnalyzeTextResponse, TranslationRequest, TranslationResponse
from app.services.language_service import language_service

router = APIRouter()


@router.post("/translate", response_model=TranslationResponse)
async def translate(
    request: TranslationRequest,
    _current_user: User | None = Depends(deps.get_optional_user)
):
    return language_service.translate(request)


@router.post("/analyze", response_model=AnalyzeTextResponse)
async def analyze(
    request: AnalyzeTextRequest,
    _current_user: User | None = Depends(deps.get_optional_user)
):
    normalized_text = (
        request.text
        if request.language == "ja"
        else language_service.translate_text(request.text, request.language, "ja")
    )
    return AnalyzeTextResponse(
        text=request.text,
        language=request.language,
        normalized_text=normalized_text,
        sentences=language_service.build_sentence_displays(normalized_text),
        analysis=language_service.analyze_text(normalized_text),
        kanji=language_service.extract_kanji_items(normalized_text),
    )
