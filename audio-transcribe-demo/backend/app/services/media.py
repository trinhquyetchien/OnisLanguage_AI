import subprocess
import tempfile
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.config import ALLOWED_EXTENSIONS, SAMPLE_RATE, VIDEO_EXTENSIONS


def get_extension(filename: str) -> str:
    return Path(filename).suffix.lower()


def validate_upload(upload: UploadFile) -> str:
    extension = get_extension(upload.filename or "")
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {extension or 'unknown'}",
        )
    return extension


def is_video_file(file_path: Path) -> bool:
    return file_path.suffix.lower() in VIDEO_EXTENSIONS


def extract_audio_from_video(video_path: Path, temp_dir: tempfile.TemporaryDirectory[str]) -> Path:
    output_path = Path(temp_dir.name) / f"{video_path.stem}.wav"
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(video_path),
                "-vn",
                "-ac",
                "1",
                "-ar",
                str(SAMPLE_RATE),
                str(output_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ffmpeg is required to transcribe video uploads.",
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exc.stderr or "Could not extract audio from video.",
        ) from exc

    return output_path
