from pathlib import Path


DEMO_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = DEMO_DIR.parent
BACKEND_DIR = DEMO_DIR / "backend"
APP_DIR = BACKEND_DIR / "app"
STORAGE_DIR = BACKEND_DIR / "storage"
UPLOAD_DIR = STORAGE_DIR / "uploads"
LOCAL_MODEL_DIR = APP_DIR / "model-transcribe-v1"
ROOT_MODEL_DIR = PROJECT_ROOT / "model-transcribe-v1"
MODEL_DIR = LOCAL_MODEL_DIR if LOCAL_MODEL_DIR.exists() else ROOT_MODEL_DIR

ALLOWED_EXTENSIONS = {
    ".mp3",
    ".wav",
    ".m4a",
    ".mp4",
    ".flac",
    ".ogg",
    ".aac",
    ".webm",
    ".mov",
    ".mkv",
}

VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".mkv"}

SAMPLE_RATE = 16000
CHUNK_LENGTH_SECONDS = 30
CHUNK_STRIDE_SECONDS = 5

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
