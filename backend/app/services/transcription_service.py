import logging
import whisper
import torch
from pathlib import Path
from typing import Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

class TranscriptionService:
    def __init__(self):
        self.model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def load(self):
        """Public method to pre-load resources"""
        self._load_model()

    def _load_model(self):
        if self.model is None:
            logger.info(f"Loading Whisper model ({settings.WHISPER_MODEL}) on {self.device}...")
            self.model = whisper.load_model(settings.WHISPER_MODEL, device=self.device)

    def transcribe(self, audio_path: Path) -> Dict[str, Any]:
        self._load_model()
        
        try:
            # Transcribe with timestamps
            result = self.model.transcribe(
                str(audio_path), 
                task="transcribe", 
                language="ja",
                verbose=False
            )
            
            segments = []
            for i, seg in enumerate(result.get("segments", [])):
                segments.append({
                    "segment_id": i,
                    "start": round(float(seg["start"]), 2),
                    "end": round(float(seg["end"]), 2),
                    "text_ja": seg["text"].strip()
                })
                
            return {
                "audio_filename": audio_path.name,
                "full_text_ja": result["text"].strip(),
                "segments": segments,
                "duration": round(segments[-1]["end"], 2) if segments else 0
            }
        except Exception as e:
            logger.error(f"Error in TranscriptionService: {e}")
            raise e

transcription_service = TranscriptionService()
