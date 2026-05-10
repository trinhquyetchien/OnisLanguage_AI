from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import settings
from app.engine.transcribe import transcribe_engine
from app.engine.kanji import kanji_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Pre-warming AI models...")
    try:
        transcribe_engine.load()
    except Exception as exc:
        print(f"Transcription model pre-warm failed: {exc}")
    try:
        kanji_engine.load()
    except Exception as exc:
        print(f"Kanji model pre-warm failed: {exc}")
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description=settings.PROJECT_DESCRIPTION,
    docs_url=settings.DOCS_URL,
    redoc_url=settings.REDOC_URL,
    openapi_url=settings.OPENAPI_URL,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/media", StaticFiles(directory=settings.UPLOAD_DIR), name="media")
app.include_router(api_router, prefix=settings.API_V1_STR)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
