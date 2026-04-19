import re
import tempfile
import threading
import logging
from pathlib import Path
from typing import Any

import librosa
import numpy as np
import torch
from fastapi import HTTPException, status
from transformers import pipeline

from app.config import CHUNK_LENGTH_SECONDS, CHUNK_STRIDE_SECONDS, MODEL_DIR, SAMPLE_RATE
from app.services.media import extract_audio_from_video, is_video_file


logger = logging.getLogger(__name__)


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def is_repetitive_text(text: str) -> bool:
    compact = text.replace(" ", "")
    if len(compact) < 12:
        return False

    if len(set(compact)) / max(len(compact), 1) < 0.15:
        return True

    for size in range(2, min(12, len(compact) // 2 + 1)):
        token = compact[:size]
        if token and compact.count(token) >= 4:
            return True
    return False


def normalize_segments(raw_segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    for raw in raw_segments:
        timestamp = raw.get("timestamp")
        text = clean_text(raw.get("text", ""))
        if not timestamp or not text:
            continue

        start, end = timestamp
        if start is None:
            continue
        if end is None or end <= start:
            end = start + 0.01
        if is_repetitive_text(text):
            continue

        segments.append(
            {
                "segment_id": len(segments),
                "start": round(float(start), 2),
                "end": round(float(end), 2),
                "text_ja": text,
            }
        )

    deduped: list[dict[str, Any]] = []
    for segment in segments:
        if deduped and segment["text_ja"] == deduped[-1]["text_ja"] and abs(segment["start"] - deduped[-1]["start"]) < 0.75:
            continue
        deduped.append(segment)
    return deduped


class LocalTranscriber:
    def __init__(self, model_path: Path) -> None:
        self.model_path = model_path
        self._pipeline = None
        self._lock = threading.Lock()

    def _load_pipeline(self):
        if self._pipeline is not None:
            return self._pipeline

        with self._lock:
            if self._pipeline is None:
                device = 0 if torch.cuda.is_available() else -1
                self._pipeline = pipeline(
                    task="automatic-speech-recognition",
                    model=str(self.model_path),
                    tokenizer=str(self.model_path),
                    feature_extractor=str(self.model_path),
                    device=device,
                )
                self._normalize_generation_config()
        return self._pipeline

    def _normalize_generation_config(self) -> None:
        if self._pipeline is None:
            return

        generation_config = self._pipeline.model.generation_config

        for field_name in ("eos_token_id", "bos_token_id", "pad_token_id", "decoder_start_token_id"):
            value = getattr(generation_config, field_name, None)
            if isinstance(value, (list, tuple)) and len(value) == 1:
                setattr(generation_config, field_name, int(value[0]))
            elif value is not None and not isinstance(value, int):
                try:
                    setattr(generation_config, field_name, int(value))
                except (TypeError, ValueError):
                    continue

    def _load_audio_array(self, source_path: Path) -> np.ndarray:
        try:
            audio, _ = librosa.load(str(source_path), sr=SAMPLE_RATE, mono=True)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not decode audio: {exc}",
            ) from exc

        if audio.size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded media contains no readable audio.",
            )

        return np.asarray(audio, dtype=np.float32)

    def _transcribe_with_timestamps(self, audio: np.ndarray) -> dict[str, Any]:
        asr = self._load_pipeline()
        return asr(
            {"raw": audio, "sampling_rate": SAMPLE_RATE},
            return_timestamps=True,
            chunk_length_s=CHUNK_LENGTH_SECONDS,
            stride_length_s=CHUNK_STRIDE_SECONDS,
            batch_size=8,
            generate_kwargs={"language": "ja", "task": "transcribe"},
        )

    def _transcribe_fallback(self, audio: np.ndarray) -> dict[str, Any]:
        asr = self._load_pipeline()
        duration = len(audio) / SAMPLE_RATE
        step = max(CHUNK_LENGTH_SECONDS - CHUNK_STRIDE_SECONDS, 1)
        start = 0.0
        chunks: list[dict[str, Any]] = []

        while start < duration:
            end = min(duration, start + CHUNK_LENGTH_SECONDS)
            start_sample = int(start * SAMPLE_RATE)
            end_sample = int(end * SAMPLE_RATE)
            clip = audio[start_sample:end_sample]
            if clip.size == 0:
                break

            result = asr(
                {"raw": clip, "sampling_rate": SAMPLE_RATE},
                batch_size=1,
                generate_kwargs={"language": "ja", "task": "transcribe"},
            )
            text = clean_text(result.get("text", ""))
            if text:
                chunks.append({"timestamp": (start, end), "text": text})

            if end >= duration:
                break
            start += step

        return {"text": " ".join(chunk["text"] for chunk in chunks), "chunks": chunks}

    def transcribe(self, media_path: Path, original_filename: str) -> dict[str, Any]:
        temp_dir: tempfile.TemporaryDirectory[str] | None = None
        source_path = media_path

        if is_video_file(media_path):
            temp_dir = tempfile.TemporaryDirectory()
            source_path = extract_audio_from_video(media_path, temp_dir)

        try:
            audio = self._load_audio_array(source_path)
            duration = round(len(audio) / SAMPLE_RATE, 2)
            segments: list[dict[str, Any]] = []
            full_text = ""

            try:
                result = self._transcribe_with_timestamps(audio)
                segments = normalize_segments(result.get("chunks", []))
                full_text = clean_text(result.get("text", ""))
            except Exception as exc:
                logger.warning("Timestamp pipeline failed, falling back to manual chunking: %s", exc)

            if not segments:
                fallback = self._transcribe_fallback(audio)
                segments = normalize_segments(fallback.get("chunks", []))
                full_text = clean_text(fallback.get("text", "")) or full_text

            if not segments and full_text:
                segments = [
                    {
                        "segment_id": 0,
                        "start": 0.0,
                        "end": duration,
                        "text_ja": full_text,
                    }
                ]

            return {
                "audio_filename": original_filename,
                "duration": duration,
                "full_text_ja": full_text,
                "segments": segments,
            }
        finally:
            if temp_dir is not None:
                temp_dir.cleanup()


transcriber = LocalTranscriber(MODEL_DIR)
