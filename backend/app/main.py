from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.api import ocr, transcribe, kanji

from contextlib import asynccontextmanager
from app.services.ocr_service import ocr_service
from app.services.transcription_service import transcription_service
from app.services.kanji_service import kanji_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-warm models on startup
    print("Pre-warming AI models...")
    # kanji_service.load() # Uncomment if you want to load at start (can be slow)
    # transcription_service.load()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Unified AI Platform for Japanese Language Learning",
    lifespan=lifespan
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount media storage
app.mount("/media", StaticFiles(directory=settings.UPLOAD_DIR), name="media")

# Include routers
app.include_router(ocr.router, prefix="/api/ocr", tags=["OCR"])
app.include_router(transcribe.router, prefix="/api/transcribe", tags=["Transcription"])
app.include_router(kanji.router, prefix="/api/kanji", tags=["Kanji Recognition"])

@app.get("/health")
async def health_check():
    return {"status": "ok", "project": settings.PROJECT_NAME}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
