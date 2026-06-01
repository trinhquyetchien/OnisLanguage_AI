from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from uuid import uuid4
from pathlib import Path
from typing import Any, Dict

import torch

from app.core.config import resolve_hf_local_snapshot, settings
from app.core.cuda_runtime import bootstrap_cuda_library_path, preload_ctranslate2_cuda_libraries
from app.services.language_service import language_service

logger = logging.getLogger(__name__)

bootstrap_cuda_library_path()


@dataclass
class DownloadedMedia:
    path: Path
    media_kind: str
    title: str


class TranscriptionService:
    def __init__(self) -> None:
        self.model = None
        self.device = self._resolve_device()
        self.compute_type = "float16" if self.device == "cuda" else "int8"

    @staticmethod
    def _resolve_device() -> str:
        requested = settings.WHISPER_DEVICE
        if requested == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        if requested == "cuda" and torch.cuda.is_available():
            return "cuda"
        return "cpu"

    def load(self) -> None:
        self._load_model()

    @staticmethod
    def _should_retry_on_cpu(exc: Exception) -> bool:
        message = str(exc).lower()
        return any(token in message for token in ("cuda", "cublas", "cudnn", "out of memory"))

    def _reset_to_cpu(self) -> None:
        logger.warning("Resetting Faster-Whisper runtime to CPU int8.")
        self.model = None
        self.device = "cpu"
        self.compute_type = "int8"

    def _resolve_model_path(self) -> tuple[str, Path]:
        preferred_models = [
            settings.WHISPER_MODEL,
            "Systran/faster-whisper-large-v3",
        ]

        checked_models: list[str] = []
        for model_name in preferred_models:
            if model_name in checked_models:
                continue
            checked_models.append(model_name)
            try:
                model_path = resolve_hf_local_snapshot(settings.WHISPER_MODEL_DIR, model_name)
            except FileNotFoundError:
                continue
            if (model_path / "model.bin").exists():
                return model_name, model_path
            logger.warning("Whisper snapshot for %s is missing model.bin at %s", model_name, model_path)

        for candidate in sorted(settings.WHISPER_MODEL_DIR.glob("models--*/snapshots/*")):
            if (candidate / "model.bin").exists():
                return candidate.parent.parent.name.replace("models--", "").replace("--", "/"), candidate

        raise FileNotFoundError(
            f"No usable Faster-Whisper snapshot with model.bin found under {settings.WHISPER_MODEL_DIR}"
        )

    def _load_model(self) -> None:
        if self.model is None:
            from faster_whisper import WhisperModel

            model_name, model_path = self._resolve_model_path()
            logger.info("Loading Faster-Whisper model (%s) from local snapshot %s on %s...", model_name, model_path, self.device)
            try:
                if self.device == "cuda":
                    preload_ctranslate2_cuda_libraries()
                self.model = WhisperModel(
                    str(model_path),
                    device=self.device,
                    compute_type=self.compute_type,
                )
            except RuntimeError as exc:
                if self.device == "cuda":
                    logger.warning(
                        "Whisper CUDA load failed (%s). Falling back to CPU int8 for model %s.",
                        exc,
                        model_name,
                    )
                    self.device = "cpu"
                    self.compute_type = "int8"
                    self.model = WhisperModel(
                        str(model_path),
                        device=self.device,
                        compute_type=self.compute_type,
                    )
                else:
                    raise

    def prepare_audio_source(self, media_path: Path, media_kind: str) -> Path:
        if media_kind == "audio":
            return media_path

        extracted_audio_path = media_path.with_suffix(".wav")
        command = [
            settings.FFMPEG_BIN,
            "-y",
            "-i",
            str(media_path),
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            str(extracted_audio_path),
        ]
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").strip()
            raise RuntimeError(f"ffmpeg audio extraction failed for {media_path.name}: {stderr or exc}") from exc
        return extracted_audio_path

    def probe_duration(self, media_path: Path) -> float | None:
        command = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(media_path),
        ]
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            duration_text = (result.stdout or "").strip()
            if not duration_text:
                return None
            return round(float(duration_text), 2)
        except Exception:
            return None

    def download_youtube_media(self, url: str) -> DownloadedMedia:
        url = url.strip()
        title = self._fetch_youtube_title(url)
        attempts = [
            {
                "media_kind": "video",
                "command": [
                    settings.YT_DLP_BIN,
                    "--no-playlist",
                    "--restrict-filenames",
                    "--no-warnings",
                    "-f",
                    "best",
                ],
            },
            {
                "media_kind": "audio",
                "command": [
                    settings.YT_DLP_BIN,
                    "--no-playlist",
                    "--restrict-filenames",
                    "--no-warnings",
                    "-x",
                    "--audio-format",
                    "mp3",
                    "-f",
                    "bestaudio",
                ],
            },
        ]
        errors: list[str] = []

        for attempt in attempts:
            output_template = settings.UPLOAD_DIR / f"youtube_{uuid4().hex}.%(ext)s"
            command = attempt["command"] + ["-o", str(output_template), url]
            try:
                subprocess.run(command, check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as exc:
                stderr = (exc.stderr or "").strip()
                errors.append(stderr or str(exc))
                continue

            candidates = sorted(settings.UPLOAD_DIR.glob(output_template.name.replace("%(ext)s", "*")))
            if candidates:
                return DownloadedMedia(
                    path=candidates[0],
                    media_kind=attempt["media_kind"],
                    title=title or candidates[0].stem
                )

            errors.append("yt-dlp completed but no output media file was found.")

        raise RuntimeError(f"yt-dlp download failed: {' | '.join(errors)}")

    def _fetch_youtube_title(self, url: str) -> str:
        command = [
            settings.YT_DLP_BIN,
            "--skip-download",
            "--no-playlist",
            "--no-warnings",
            "--print",
            "%(title)s",
            url,
        ]
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError:
            return ""

        lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        return lines[-1] if lines else ""

    def transcribe(self, audio_path: Path) -> Dict[str, Any]:
        self._load_model()

        try:
            segments, info = self.model.transcribe(
                str(audio_path),
                beam_size=1,
                language="ja",
                condition_on_previous_text=False,
                word_timestamps=True,
            )

            results = []
            full_text = []
            segment_texts: list[str] = []
            pending_segments: list[dict[str, Any]] = []
            for index, segment in enumerate(segments):
                words = []
                for word in getattr(segment, "words", []) or []:
                    word_text = language_service.extract_japanese_text((getattr(word, "word", "") or "").strip())
                    if not word_text:
                        continue
                    word_display = language_service.build_text_display(word_text, include_translation=False)
                    words.append(
                        {
                            "start": round(float(getattr(word, "start", segment.start) or segment.start), 2),
                            "end": round(float(getattr(word, "end", segment.end) or segment.end), 2),
                            "text_ja": word_text,
                            "confidence": float(getattr(word, "probability", 0.0) or 0.0),
                            "text_display": word_display,
                        }
                    )
                segment_text = " ".join(word["text_ja"] for word in words).strip()
                if not segment_text:
                    segment_text = language_service.extract_japanese_text(segment.text.strip())
                if not segment_text:
                    continue
                pending_segments.append(
                    {
                        "segment_id": len(pending_segments),
                        "start": round(segment.start, 2),
                        "end": round(segment.end, 2),
                        "text_ja": segment_text,
                        "words": words,
                    }
                )
                segment_texts.append(segment_text)
                full_text.append(segment_text)

            segment_displays = language_service.build_text_displays(segment_texts, include_translation=True)
            for segment_payload, segment_display in zip(pending_segments, segment_displays):
                segment_payload["text_vi"] = segment_display.translation_vi
                segment_payload["text_display"] = segment_display
                results.append(segment_payload)

            actual_duration = self.probe_duration(audio_path)
            normalized_full_text = " ".join(full_text).strip()
            full_text_display = (
                language_service.build_text_display(normalized_full_text, include_translation=True)
                if normalized_full_text
                else None
            )

            return {
                "audio_filename": audio_path.name,
                "full_text_ja": normalized_full_text,
                "full_text_vi": full_text_display.translation_vi if full_text_display else None,
                "text_display": full_text_display,
                "analysis": language_service.build_fast_analysis(normalized_full_text) if normalized_full_text else None,
                "segments": results,
                "duration": actual_duration if actual_duration is not None else round(info.duration, 2),
                "language_probability": info.language_probability
            }
        except Exception as exc:
            if self.device == "cuda" and self._should_retry_on_cpu(exc):
                logger.warning(
                    "Whisper inference failed on CUDA (%s). Retrying transcription on CPU int8.",
                    exc,
                )
                self._reset_to_cpu()
                self._load_model()
                return self.transcribe(audio_path)
            logger.error("Error in TranscriptionService: %s", exc)
            raise


transcribe_engine = TranscriptionService()
