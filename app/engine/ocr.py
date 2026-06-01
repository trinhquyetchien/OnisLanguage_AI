from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

from app.core.config import settings

logger = logging.getLogger(__name__)


class OCRService:
    def __init__(self) -> None:
        self.runtime_python = settings.BASE_DIR / ".runtime-venv" / "bin" / "python"
        self.worker_script = settings.BASE_DIR / "app" / "engine" / "paddle_ocr_worker.py"
        self.model_dir = settings.OCR_MODEL_DIR / "paddle"

    def load(self) -> None:
        if self.runtime_python.exists():
            return
        raise RuntimeError(
            f"OCR runtime not found at {self.runtime_python}. "
            "Create the runtime venv and install PaddleOCR before using image OCR."
        )

    def process_image(self, image_path: Path) -> Dict[str, Any]:
        self.load()

        try:
            command = [
                str(self.runtime_python),
                str(self.worker_script),
                str(image_path),
                str(self.model_dir),
            ]
            env = os.environ.copy()
            env["PADDLE_HOME"] = str(self.model_dir)
            completed = subprocess.run(command, check=True, capture_output=True, text=True, env=env)
            return json.loads(completed.stdout)
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").strip()
            stdout = (exc.stdout or "").strip()
            detail = stderr or stdout or str(exc)
            logger.error("PaddleOCR worker failed: %s", detail)
            raise RuntimeError(f"PaddleOCR worker failed: {detail}") from exc
        except json.JSONDecodeError as exc:
            logger.error("Invalid OCR worker JSON: %s", exc)
            raise RuntimeError("PaddleOCR worker returned invalid JSON.") from exc
        except Exception as exc:
            logger.error("Error in OCRService: %s", exc)
            raise


ocr_engine = OCRService()
