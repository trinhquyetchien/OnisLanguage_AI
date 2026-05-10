import os
import whisper
from paddleocr import PaddleOCR
import torch
from app.engine.kanji import kanji_engine
from app.core.config import settings

def setup():
    print("--- Starting AI Models Setup ---")
    
    # 1. Setup Whisper
    model_name = settings.WHISPER_MODEL
    print(f"Downloading/Verifying Whisper model: {model_name}...")
    whisper.load_model(model_name)
    print("✓ Whisper model ready.")

    # 2. Setup PaddleOCR
    print(f"Downloading/Verifying PaddleOCR models (lang={settings.OCR_LANG})...")
    PaddleOCR(use_textline_orientation=True, lang=settings.OCR_LANG)
    print("✓ PaddleOCR models ready.")

    # 3. Verify Kanji Model
    print("Verifying Kanji Recognition model...")
    try:
        kanji_engine.load()
        if kanji_engine.model:
            print("✓ Kanji model loaded successfully.")
        else:
            print("✗ Kanji model loading failed (check data/models path).")
    except Exception as e:
        print(f"✗ Error loading Kanji model: {e}")

    print("--- All AI Models are set up and ready! ---")

if __name__ == "__main__":
    setup()
