import logging
from typing import Dict, Any, List
from paddleocr import PaddleOCR
from pathlib import Path
from app.core.config import settings

import torch

logger = logging.getLogger(__name__)

class OCRService:
    def __init__(self):
        self.ocr = None
        self.use_gpu = torch.cuda.is_available()

    def _get_model(self):
        if self.ocr is None:
            logger.info(f"Initializing PaddleOCR model (use_gpu={self.use_gpu})...")
            self.ocr = PaddleOCR(
                use_angle_cls=True, 
                lang=settings.OCR_LANG, 
                show_log=False,
                use_gpu=self.use_gpu
            )
        return self.ocr

    def process_image(self, image_path: Path) -> Dict[str, Any]:
        try:
            ocr = self._get_model()
            result = ocr.ocr(str(image_path), cls=True)
            
            blocks = []
            full_text_parts = []
            
            if result and result[0]:
                for line in result[0]:
                    box = line[0]
                    text, confidence = line[1]
                    
                    blocks.append({
                        "text": text,
                        "confidence": float(confidence),
                        "box": box
                    })
                    full_text_parts.append(text)
            
            return {
                "full_text": "\n".join(full_text_parts),
                "blocks": blocks
            }
        except Exception as e:
            logger.error(f"Error in OCRService: {e}")
            raise e

ocr_service = OCRService()
