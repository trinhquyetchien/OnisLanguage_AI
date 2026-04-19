import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import MODEL_DIR, UPLOAD_DIR, VIDEO_EXTENSIONS
from app.schemas import HealthResponse, TranscriptResponse
from app.services.infer import transcriber
from app.services.media import validate_upload


app = FastAPI(title="Onis Japanese Media Transcriber", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/media", StaticFiles(directory=UPLOAD_DIR), name="media")


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(status="ok", model_path=str(MODEL_DIR))


@app.post("/api/transcribe", response_model=TranscriptResponse)
async def transcribe_media(file: UploadFile = File(...)) -> TranscriptResponse:
    validate_upload(file)

    original_name = Path(file.filename or "upload").name
    stored_name = f"{uuid4().hex}_{original_name}"
    stored_path = UPLOAD_DIR / stored_name

    with stored_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    payload = transcriber.transcribe(stored_path, original_name)
    payload["media_url"] = f"/media/{stored_name}"
    payload["media_kind"] = "video" if stored_path.suffix.lower() in VIDEO_EXTENSIONS else "audio"
    return TranscriptResponse.model_validate(payload)
