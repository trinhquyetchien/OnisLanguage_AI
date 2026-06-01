from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List

from sudachipy import dictionary, tokenizer

from app.core.config import settings

logger = logging.getLogger(__name__)


class JapaneseStructureService:
    def __init__(self) -> None:
        self.dict = None
        self.tokenizer_obj = None
        # Sudachi doesn't easily support redirecting the dictionary download 
        # like Whisper or PaddleOCR via simple parameters, but we can 
        # potentially point to a system dictionary file if we download it manually.
        # For now, we'll initialize it and see where it goes.

    def _get_tokenizer(self):
        if self.dict is None:
            logger.info("Initializing SudachiPy dictionary...")
            try:
                # Default uses sudachidict_core
                self.dict = dictionary.Dictionary()
                self.tokenizer_obj = self.dict.create()
            except Exception as e:
                logger.error(f"Failed to initialize SudachiPy: {e}")
                raise
        return self.tokenizer_obj

    def analyze(self, text: str) -> List[Dict[str, Any]]:
        tk = self._get_tokenizer()
        # Mode.C is usually best for "structure analysis" as it gives the longest possible morphemes
        mode = tokenizer.Tokenizer.SplitMode.C
        tokens = tk.tokenize(text, mode)
        
        results = []
        for m in tokens:
            results.append({
                "surface": m.surface(),
                "reading": m.reading_form(),
                "normalized": m.normalized_form(),
                "dictionary_form": m.dictionary_form(),
                "pos": m.part_of_speech(), # Returns a tuple like ('名詞', '固有名詞', '地名', '国', '*', '*')
            })
        return results

japanese_structure_engine = JapaneseStructureService()
