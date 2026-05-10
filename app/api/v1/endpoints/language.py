from fastapi import APIRouter, Depends

from app.api import deps
from app.db.models import User
from app.schemas.language import AnalyzeTextRequest, AnalyzeTextResponse, TranslationRequest, TranslationResponse
from app.services.language_service import language_service

router = APIRouter()


@router.post("/translate", response_model=TranslationResponse)
async def translate(
    request: TranslationRequest,
    current_user: User = Depends(deps.get_current_user)
):
    return language_service.translate(request)


@router.post("/analyze", response_model=AnalyzeTextResponse)
async def analyze(
    request: AnalyzeTextRequest,
    current_user: User = Depends(deps.get_current_user)
):
    return AnalyzeTextResponse(
        text=request.text,
        language=request.language,
        analysis=language_service.analyze_text(request.text),
    )
