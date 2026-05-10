from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

import torch
import whisper

from app.core.config import settings

logger = logging.getLogger(__name__)


class TranscriptionService:
    def __init__(self) -> None:
        self.model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def load(self) -> None:
        self._load_model()

    def _load_model(self) -> None:
        if self.model is None:
            logger.info("Loading Whisper model (%s) on %s...", settings.WHISPER_MODEL, self.device)
            self.model = whisper.load_model(settings.WHISPER_MODEL, device=self.device)

    def transcribe(self, audio_path: Path) -> Dict[str, Any]:
        self._load_model()

        try:
            result = self.model.transcribe(
                str(audio_path),
                task="transcribe",
                language="ja",
                verbose=False,
            )

            segments = []
            for i, seg in enumerate(result.get("segments", [])):
                segments.append(
                    {
                        "segment_id": i,
                        "start": round(float(seg["start"]), 2),
                        "end": round(float(seg["end"]), 2),
                        "text_ja": seg["text"].strip(),
                    }
                )

            return {
                "audio_filename": audio_path.name,
                "full_text_ja": result["text"].strip(),
                "segments": segments,
                "duration": round(segments[-1]["end"], 2) if segments else 0,
            }
        except Exception as exc:
            logger.error("Error in TranscriptionService: %s", exc)
            raise


transcribe_engine = TranscriptionService()
