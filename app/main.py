from contextlib import asynccontextmanager
import logging
from app.core.cuda_runtime import bootstrap_cuda_library_path


bootstrap_cuda_library_path()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles

from app.admin import admin_router
from app.api.router import api_router
from app.core.config import settings
from app.db import models  # noqa: F401
from app.db.session import Base, engine
from app.engine.transcribe import transcribe_engine
from app.engine.kanji import kanji_engine
from app.engine.ocr import ocr_engine
from app.engine.chat import chat_engine
from app.engine.language_structure import japanese_structure_engine
from app.services.auth_service import auth_service

logger = logging.getLogger("onis.startup")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    print("Seeding database...")
    try:
        auth_service.seed_dummy_user()
    except Exception as exc:
        print(f"Database seeding failed: {exc}")

    # Load all AI resources during startup so the first request does not pay the
    # model initialization cost. If one model is unavailable, startup should fail
    # loudly instead of serving a half-ready backend.
    startup_loaders = [
        ("Sudachi tokenizer", lambda: japanese_structure_engine.analyze("日本語")),
        ("OCR runtime", ocr_engine.load),
        ("Whisper transcription model", transcribe_engine.load),
        ("Kanji model", kanji_engine.load),
        ("Chat model", chat_engine.load),
    ]

    for label, loader in startup_loaders:
        logger.info("Pre-warming %s...", label)
        try:
            loader()
            logger.info("Pre-warmed %s successfully.", label)
        except Exception as exc:
            logger.exception("Pre-warm failed for %s: %s", label, exc)
            raise RuntimeError(f"Startup aborted while loading {label}: {exc}") from exc
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
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SESSION_SECRET_KEY,
    session_cookie="onis_admin_session",
    same_site="lax",
    https_only=False,
)

app.mount("/media", StaticFiles(directory=settings.UPLOAD_DIR), name="media")
app.mount("/kanji-assets", StaticFiles(directory=settings.KANJI_ASSETS_DIR), name="kanji-assets")
app.mount("/admin-static", StaticFiles(directory=settings.STATIC_DIR / "admin"), name="admin-static")
app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(admin_router)

if __name__ == "__main__":
    import uvicorn

    # Only watch the 'app' directory for changes. 
    # This prevents reload loops from data/models and fixes startup hangs.
    uvicorn.run(
        "app.main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        reload_dirs=["app"]
    )
