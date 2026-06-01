import os
import time
import logging
import torch
from app.engine.kanji import kanji_engine
from app.engine.ocr import ocr_engine
from app.engine.transcribe import transcribe_engine
from app.engine.chat import chat_engine
from app.engine.language_structure import japanese_structure_engine
from app.core.config import settings

def _build_logger() -> logging.Logger:
    log_dir = settings.DATA_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "model_prewarm.log"

    logger = logging.getLogger("model_prewarm")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    logger.propagate = False
    return logger

def setup():
    logger = _build_logger()
    print("🚀 --- Starting TOP-TIER AI Models Setup --- 🚀")
    logger.info("Starting model prewarm setup.")
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    logger.info("Runtime device: %s", device)

    startup_loaders = [
        ("Sudachi tokenizer", lambda: japanese_structure_engine.analyze("日本語")),
        ("OCR runtime", ocr_engine.load),
        ("Whisper transcription model", transcribe_engine.load),
        ("Kanji model", kanji_engine.load),
        ("Chat model", chat_engine.load),
    ]

    for label, loader in startup_loaders:
        print(f"Pre-warming {label}...")
        logger.info("Pre-warming started: %s", label)
        started = time.perf_counter()
        try:
            loader()
            print(f"✓ {label} ready.")
            elapsed = time.perf_counter() - started
            logger.info("Pre-warming success: %s (%.2fs)", label, elapsed)
        except Exception as e:
            print(f"✗ {label} failed: {e}")
            elapsed = time.perf_counter() - started
            logger.exception("Pre-warming failed: %s after %.2fs", label, elapsed)
            raise

    print("\n✅ --- All WORLD-CLASS AI Models are set up and ready! --- ✅")
    print(f"All models stored in: {settings.MODELS_DIR}")
    logger.info("All model prewarm tasks completed.")

if __name__ == "__main__":
    setup()
