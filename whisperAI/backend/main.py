import os
import tempfile
import time
from pathlib import Path

import whisper
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sudachipy import dictionary
from sudachipy import tokenizer


BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
MODEL_NAME = os.getenv("WHISPER_MODEL", "base")
WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "ja")

app = FastAPI(title="Whisper AI Local Transcriber")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model = None
japanese_tokenizer = None


class AnalyzeRequest(BaseModel):
    text: str


def katakana_to_hiragana(text: str) -> str:
    return "".join(chr(ord(char) - 0x60) if "ァ" <= char <= "ン" else char for char in text)


def has_kanji(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def get_japanese_tokenizer():
    global japanese_tokenizer
    if japanese_tokenizer is None:
        japanese_tokenizer = dictionary.Dictionary().create()
    return japanese_tokenizer


def get_model():
    global model
    if model is None:
        model = whisper.load_model(MODEL_NAME)
    return model


def analyze_japanese(text: str):
    if not text:
        return []

    mode = tokenizer.Tokenizer.SplitMode.C
    tokens = []
    for index, morpheme in enumerate(get_japanese_tokenizer().tokenize(text, mode)):
        surface = morpheme.surface()
        reading = morpheme.reading_form()
        reading_hiragana = katakana_to_hiragana(reading) if reading and reading != "*" else ""
        part_of_speech = [item for item in morpheme.part_of_speech() if item != "*"]

        tokens.append(
            {
                "id": index,
                "surface": surface,
                "reading": reading_hiragana,
                "reading_katakana": reading if reading != "*" else "",
                "lemma": morpheme.dictionary_form(),
                "pos": part_of_speech,
                "pos_text": " / ".join(part_of_speech),
                "has_kanji": has_kanji(surface),
            }
        )

    return tokens


@app.get("/api/health")
def health():
    return {"status": "ok", "model": MODEL_NAME, "language": WHISPER_LANGUAGE, "analyzer": "SudachiPy"}


@app.post("/api/analyze")
def analyze(request: AnalyzeRequest):
    text = request.text.strip()
    return {"text": text, "tokens": analyze_japanese(text)}


@app.post("/api/transcribe")
async def transcribe(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Vui long chon file am thanh hoac video.")

    suffix = Path(file.filename).suffix or ".tmp"
    started_at = time.perf_counter()

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_path = Path(temp_file.name)
            while chunk := await file.read(1024 * 1024):
                temp_file.write(chunk)

        result = get_model().transcribe(str(temp_path), language=WHISPER_LANGUAGE, fp16=False)
        duration = round(time.perf_counter() - started_at, 2)
        segments = [
            {
                "id": index,
                "start": round(float(segment.get("start", 0)), 2),
                "end": round(float(segment.get("end", 0)), 2),
                "text": segment.get("text", "").strip(),
                "tokens": analyze_japanese(segment.get("text", "").strip()),
            }
            for index, segment in enumerate(result.get("segments", []))
        ]
        text = result.get("text", "").strip()

        return {
            "text": text,
            "language": result.get("language"),
            "segments": segments,
            "tokens": analyze_japanese(text),
            "duration_seconds": duration,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Khong the xu ly file: {exc}") from exc
    finally:
        if "temp_path" in locals() and temp_path.exists():
            temp_path.unlink()


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(FRONTEND_DIR / "index.html")
