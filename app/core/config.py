from pathlib import Path
import os

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]
LOCAL_YT_DLP_BIN = BASE_DIR / ".yt-dlp-venv" / "bin" / "yt-dlp"


class Settings(BaseSettings):
    BASE_DIR: Path = BASE_DIR
    model_config = SettingsConfigDict(
        case_sensitive=True, 
        env_file=Path(__file__).resolve().parents[2] / ".env", 
        extra="ignore"
    )

    PROJECT_NAME: str = "OnisLanguage AI Backend"
    PROJECT_DESCRIPTION: str = (
        "Backend API for Japanese learning tools: OCR, speech-to-text, "
        "audio/video transcription, kanji recognition, practice exams, and flashcards."
    )
    API_V1_STR: str = "/api/v1"
    DOCS_URL: str = "/docs"
    REDOC_URL: str = "/redoc"
    OPENAPI_URL: str = "/openapi.json"

    DATA_DIR: Path = BASE_DIR / "data"
    STATIC_DIR: Path = BASE_DIR / "app" / "static"
    TEMPLATES_DIR: Path = BASE_DIR / "app" / "templates"
    STORAGE_DIR: Path = DATA_DIR / "uploads"
    UPLOAD_DIR: Path = STORAGE_DIR
    MODELS_DIR: Path = DATA_DIR / "models"
    KANJI_DATA_DIR: Path = DATA_DIR / "kanji"
    KANJI_METADATA_DIR: Path = KANJI_DATA_DIR / "metadata"
    KANJI_ASSETS_DIR: Path = KANJI_DATA_DIR / "assets"
    KANJI_IMAGES_DIR: Path = KANJI_ASSETS_DIR / "images"
    KANJI_SVG_DIR: Path = KANJI_ASSETS_DIR / "svg"
    OCR_MODEL_DIR: Path = MODELS_DIR / "paddleocr"
    WHISPER_MODEL_DIR: Path = MODELS_DIR / "whisper"
    CHAT_MODEL_DIR: Path = MODELS_DIR / "chat"
    YT_DLP_BIN: str = str(LOCAL_YT_DLP_BIN if LOCAL_YT_DLP_BIN.exists() else "yt-dlp")
    FFMPEG_BIN: str = "ffmpeg"

    ALLOWED_ORIGINS: list[str] = ["*"]

    # AI Model Settings (Top-Tier Re-architecture)
    OCR_MODEL: str = "microsoft/trocr-large-japanese"
    WHISPER_MODEL: str = "kotoba-tech/kotoba-whisper-v2.0-faster"
    CHAT_MODEL: str = "Qwen/Qwen2.5-1.5B-Instruct" # Sịn và nhẹ cho local
    WHISPER_DEVICE: str = "cuda"
    CHAT_DEVICE: str = "cuda"
    KANJI_DEVICE: str = "cuda"
    
    KANJI_MODEL_TYPE: str = "swin_transformer" # Upgraded from resnet
    KANJI_MODEL_PATH: Path = MODELS_DIR / "best_etl9g_resnet18_stroke_mixed.pth"
    KANJI_LABEL_MAP_PATH: Path = MODELS_DIR / "label_map.csv" # 6000+ characters
    
    DATABASE_URL: str = "postgresql://user:pass@localhost:5432/db"

    # JWT Settings
    SECRET_KEY: str = "secret"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    SESSION_SECRET_KEY: str = "admin-session-secret"
    ADMIN_TITLE: str = "Onis Admin Hub"
    ADMIN_EMAILS: list[str] = ["demo@onis.app"]

    # SMTP Settings (Gmail Example)
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_FROM: str = "noreply@onis.app"
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    USE_CREDENTIALS: bool = True

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def _parse_origins(cls, value):
        if value is None:
            return ["*"]
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("ADMIN_EMAILS", mode="before")
    @classmethod
    def _parse_admin_emails(cls, value):
        if value is None:
            return ["demo@onis.app"]
        if isinstance(value, str):
            return [item.strip().lower() for item in value.split(",") if item.strip()]
        return [str(item).strip().lower() for item in value if str(item).strip()]

    @field_validator("WHISPER_DEVICE", "CHAT_DEVICE", "KANJI_DEVICE", mode="before")
    @classmethod
    def _normalize_device(cls, value):
        normalized = str(value or "cpu").strip().lower()
        if normalized not in {"cpu", "cuda", "auto"}:
            raise ValueError("Device setting must be one of: cpu, cuda, auto")
        return normalized


settings = Settings()
settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
settings.STATIC_DIR.mkdir(parents=True, exist_ok=True)
settings.TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.MODELS_DIR.mkdir(parents=True, exist_ok=True)
settings.KANJI_DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.KANJI_METADATA_DIR.mkdir(parents=True, exist_ok=True)
settings.KANJI_ASSETS_DIR.mkdir(parents=True, exist_ok=True)
settings.KANJI_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
settings.KANJI_SVG_DIR.mkdir(parents=True, exist_ok=True)
settings.OCR_MODEL_DIR.mkdir(parents=True, exist_ok=True)
settings.WHISPER_MODEL_DIR.mkdir(parents=True, exist_ok=True)
settings.CHAT_MODEL_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")


def resolve_hf_local_snapshot(cache_root: Path, model_name: str) -> Path:
    direct_dir = cache_root / f"models--{model_name.replace('/', '--')}"
    candidate_dirs = [direct_dir] if direct_dir.exists() else []

    if not candidate_dirs:
        model_hint = model_name.replace("/", "--")
        candidate_dirs = sorted(
            path for path in cache_root.glob("models--*")
            if path.is_dir() and (path.name.endswith(model_hint) or model_hint in path.name)
        )

    if not candidate_dirs:
        raise FileNotFoundError(
            f"Local Hugging Face cache not found for {model_name} under {cache_root}"
        )

    model_cache_dir = candidate_dirs[0]

    main_ref = model_cache_dir / "refs" / "main"
    if main_ref.exists():
        snapshot_name = main_ref.read_text(encoding="utf-8").strip()
        snapshot_dir = model_cache_dir / "snapshots" / snapshot_name
        if snapshot_dir.exists():
            return snapshot_dir

    snapshots_dir = model_cache_dir / "snapshots"
    candidates = sorted(path for path in snapshots_dir.iterdir() if path.is_dir()) if snapshots_dir.exists() else []
    if candidates:
        return candidates[-1]

    raise FileNotFoundError(
        f"No local snapshot found for {model_name} in {model_cache_dir}"
    )
