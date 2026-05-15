from __future__ import annotations

import logging
import os
import math
import re
from pathlib import Path
from typing import Any, Dict, List

import torch
from transformers import MarianMTModel, MarianTokenizer

from app.core.config import resolve_hf_local_snapshot, settings

logger = logging.getLogger(__name__)


class TranslationService:
    DEFAULT_MAX_SOURCE_TOKENS = 512
    DEFAULT_BATCH_SIZE = 8

    def __init__(self) -> None:
        self.model = None
        self.tokenizer = None
        self.device = torch.device(self._resolve_device())
        # Redirect HuggingFace cache to project directory
        os.environ["HF_HOME"] = str(settings.TRANSLATION_MODEL_DIR)

    @staticmethod
    def _resolve_device() -> str:
        requested = settings.TRANSLATION_DEVICE
        if requested == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        if requested == "cuda" and torch.cuda.is_available():
            return "cuda"
        return "cpu"

    def load(self) -> None:
        self._load_resources()

    @staticmethod
    def _should_retry_on_cpu(exc: Exception) -> bool:
        message = str(exc).lower()
        return any(token in message for token in ("cuda", "cublas", "cudnn", "out of memory"))

    def _reset_to_cpu(self) -> None:
        logger.warning("Resetting translation runtime to CPU.")
        self.model = None
        self.tokenizer = None
        self.device = torch.device("cpu")

    def _load_resources(self) -> None:
        if self.model is None:
            model_name = settings.TRANSLATION_MODEL
            model_path = resolve_hf_local_snapshot(settings.TRANSLATION_MODEL_DIR, model_name)
            logger.info("Loading translation model (%s) from local snapshot %s on %s...", model_name, model_path, self.device)
            
            self.tokenizer = MarianTokenizer.from_pretrained(
                str(model_path),
                local_files_only=True
            )
            try:
                self.model = MarianMTModel.from_pretrained(
                    str(model_path),
                    local_files_only=True
                ).to(self.device)
            except RuntimeError as exc:
                if self.device.type == "cuda" and self._should_retry_on_cpu(exc):
                    logger.warning(
                        "Translation CUDA load failed (%s). Falling back to CPU for model %s.",
                        exc,
                        model_name,
                    )
                    self._reset_to_cpu()
                    self._load_resources()
                    return
                raise

    def _max_source_tokens(self) -> int:
        model_max_length = getattr(self.tokenizer, "model_max_length", None)
        if isinstance(model_max_length, int) and 0 < model_max_length < 100000:
            return model_max_length
        return self.DEFAULT_MAX_SOURCE_TOKENS

    def _sentence_chunks(self, text: str) -> List[str]:
        parts = re.split(r"(?<=[。！？!?…\n])", text)
        return [part.strip() for part in parts if part and part.strip()]

    def _tokenize_without_special_tokens(self, text: str) -> List[int]:
        # We intentionally need the full token sequence here for chunking logic.
        # Disable the tokenizer max-length warning because truncation is handled later
        # in _translate_chunk/_translate_batch after we split long inputs ourselves.
        encoded = self.tokenizer(
            text,
            add_special_tokens=False,
            truncation=False,
            return_attention_mask=False,
            verbose=False,
        )
        return encoded["input_ids"]

    def _split_long_text(self, text: str) -> List[str]:
        max_tokens = max(32, self._max_source_tokens() - 8)
        sentences = self._sentence_chunks(text) or [text.strip()]
        chunks: List[str] = []
        current_parts: List[str] = []
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = self._tokenize_without_special_tokens(sentence)
            sentence_length = len(sentence_tokens)

            if sentence_length > max_tokens:
                if current_parts:
                    chunks.append(" ".join(current_parts).strip())
                    current_parts = []
                    current_tokens = 0

                for start in range(0, sentence_length, max_tokens):
                    token_slice = sentence_tokens[start : start + max_tokens]
                    chunk_text = self.tokenizer.decode(
                        token_slice,
                        skip_special_tokens=True,
                        clean_up_tokenization_spaces=True,
                    ).strip()
                    if chunk_text:
                        chunks.append(chunk_text)
                continue

            if current_parts and current_tokens + sentence_length > max_tokens:
                chunks.append(" ".join(current_parts).strip())
                current_parts = []
                current_tokens = 0

            current_parts.append(sentence)
            current_tokens += sentence_length

        if current_parts:
            chunks.append(" ".join(current_parts).strip())

        return [chunk for chunk in chunks if chunk]

    def _translate_chunk(self, text: str) -> str:
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=self._max_source_tokens(),
        ).to(self.device)
        with torch.no_grad():
            translated_tokens = self.model.generate(**inputs)
        return self.tokenizer.decode(translated_tokens[0], skip_special_tokens=True).strip()

    def _translate_batch(self, texts: List[str]) -> List[str]:
        if not texts:
            return []
        inputs = self.tokenizer(
            texts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=self._max_source_tokens(),
        ).to(self.device)
        with torch.no_grad():
            translated_tokens = self.model.generate(**inputs)
        return [
            self.tokenizer.decode(tokens, skip_special_tokens=True).strip()
            for tokens in translated_tokens
        ]

    def translate_many(self, texts: List[str]) -> List[str]:
        normalized_texts = [text.strip() for text in texts]
        if not any(normalized_texts):
            return ["" for _ in normalized_texts]

        self._load_resources()

        try:
            flattened_chunks: List[str] = []
            chunk_counts: List[int] = []
            for text in normalized_texts:
                if not text:
                    chunk_counts.append(0)
                    continue
                chunks = self._split_long_text(text)
                chunk_counts.append(len(chunks))
                flattened_chunks.extend(chunks)

            translated_chunks: List[str] = []
            for start in range(0, len(flattened_chunks), self.DEFAULT_BATCH_SIZE):
                batch = flattened_chunks[start : start + self.DEFAULT_BATCH_SIZE]
                translated_chunks.extend(self._translate_batch(batch))

            results: List[str] = []
            cursor = 0
            for count in chunk_counts:
                if count == 0:
                    results.append("")
                    continue
                translated = translated_chunks[cursor : cursor + count]
                cursor += count
                results.append(" ".join(part for part in translated if part).strip())
            return results
        except Exception as exc:
            logger.error("Error in TranslationService.translate_many: %s", exc)
            return [f"[Translation Error: {exc}]" if text else "" for text in normalized_texts]

    def translate(self, text: str) -> str:
        if not text.strip():
            return ""
        return self.translate_many([text])[0]


translation_engine = TranslationService()
