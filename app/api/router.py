from fastapi import APIRouter

from app.api.v1.endpoints import admin, auth, flashcards, health, kanji, language, ocr, practice, sync, transcribe, chat

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
api_router.include_router(language.router, prefix="/language", tags=["Language"])
api_router.include_router(ocr.router, prefix="/ai/ocr", tags=["AI", "OCR"])
api_router.include_router(transcribe.router, prefix="/ai/transcribe", tags=["AI", "Transcription"])
api_router.include_router(kanji.router, prefix="/ai/kanji", tags=["AI", "Kanji"])
api_router.include_router(chat.router, prefix="/ai/chat", tags=["AI", "Chat"])
api_router.include_router(practice.router, prefix="/practice", tags=["Practice Exams"])
api_router.include_router(flashcards.router, prefix="/flashcards", tags=["Flashcards"])
api_router.include_router(sync.router, prefix="/sync", tags=["Sync"])
