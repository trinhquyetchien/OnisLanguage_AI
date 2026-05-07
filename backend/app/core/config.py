from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "OnisLanguage Unified AI"
    API_V1_STR: str = "/api"
    
    BASE_DIR: Path = Path(__file__).resolve().parents[2]
    STORAGE_DIR: Path = BASE_DIR / "storage"
    UPLOAD_DIR: Path = STORAGE_DIR / "uploads"
    MODELS_DIR: Path = BASE_DIR / "models"
    
    # OCR Settings
    OCR_LANG: str = "japan"
    
    # Kanji Settings
    KANJI_MODEL_PATH: Path = MODELS_DIR / "best_etl9g_resnet18_stroke_mixed.pth"
    KANJI_LABEL_MAP_PATH: Path = MODELS_DIR / "label_map.csv"
    
    # Transcription Settings
    WHISPER_MODEL: str = "base"
    
    class Config:
        case_sensitive = True

settings = Settings()

# Ensure directories exist
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.MODELS_DIR.mkdir(parents=True, exist_ok=True)
