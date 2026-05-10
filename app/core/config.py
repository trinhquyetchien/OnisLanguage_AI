from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env", extra="ignore")

    PROJECT_NAME: str = "OnisLanguage AI Backend"
    PROJECT_DESCRIPTION: str = (
        "Backend API for Japanese learning tools: OCR, speech-to-text, "
        "audio/video transcription, kanji recognition, practice exams, and flashcards."
    )
    API_V1_STR: str = "/api/v1"
    DOCS_URL: str = "/docs"
    REDOC_URL: str = "/redoc"
    OPENAPI_URL: str = "/openapi.json"

    BASE_DIR: Path = Path(__file__).resolve().parents[2]
    DATA_DIR: Path = BASE_DIR / "data"
    STORAGE_DIR: Path = DATA_DIR / "uploads"
    UPLOAD_DIR: Path = STORAGE_DIR
    MODELS_DIR: Path = DATA_DIR / "models"

    ALLOWED_ORIGINS: list[str] = ["*"]

    OCR_LANG: str = "japan"
    WHISPER_MODEL: str = "base"
    KANJI_MODEL_PATH: Path = MODELS_DIR / "best_etl9g_resnet18_stroke_mixed.pth"
    KANJI_LABEL_MAP_PATH: Path = MODELS_DIR / "label_map.csv"
    DATABASE_URL: str = "postgresql://trinhquyetchien:onis@localhost:5432/onis_language"

    # JWT Settings
    SECRET_KEY: str = "onis_super_secret_key_change_me_later"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # SMTP Settings (Gmail Example)
    MAIL_USERNAME: str = "demo@gmail.com"
    MAIL_PASSWORD: str = "password"
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


settings = Settings()
settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.MODELS_DIR.mkdir(parents=True, exist_ok=True)
