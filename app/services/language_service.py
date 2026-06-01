from __future__ import annotations

import re
import logging
from typing import Any

from app.schemas.language import (
    AnalyzedSentence,
    FuriganaToken,
    GrammarPoint,
    JapaneseTextDisplay,
    KanjiItem,
    TextAnalysis,
    TranslationRequest,
    TranslationResponse,
    VocabularyItem,
)
from app.engine.language_structure import japanese_structure_engine
from app.engine.chat import chat_engine
from app.engine.kanji import kanji_engine

logger = logging.getLogger(__name__)


class LanguageService:
    _KANJI_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
    _JAPANESE_CHAR_RE = re.compile(
        r"[0-9０-９\u3040-\u30ff\u31f0-\u31ff\u3400-\u4dbf\u4e00-\u9fff\uff66-\uff9f\u3000-\u303f々ー]+"
    )
    MAX_LLM_ANALYSIS_CHARS = 160

    def __init__(self) -> None:
        self._translation_cache: dict[tuple[str, str, str], str] = {}

    def _translate_with_chat(self, normalized: str, source_language: str, target_language: str) -> str:
        if source_language == "ja" and target_language == "vi":
            system_prompt = (
                "Bạn là công cụ dịch Nhật sang Việt cho ứng dụng học tiếng Nhật. "
                "Nhiệm vụ: chuyển câu tiếng Nhật thành đúng 1 bản tiếng Việt tự nhiên, chính xác ngữ nghĩa. "
                "Chỉ trả về tiếng Việt. Không giải thích. Không romaji. Không markdown."
            )
            user_prompt = (
                "Dịch sang tiếng Việt tự nhiên:\n"
                f"Tiếng Nhật: {normalized}\n"
                "Tiếng Việt:"
            )
        elif source_language == "vi" and target_language == "ja":
            system_prompt = (
                "Bạn là công cụ dịch Việt sang Nhật cho ứng dụng học tiếng Nhật. "
                "Nhiệm vụ: chuyển câu tiếng Việt thành đúng 1 câu tiếng Nhật tự nhiên, ngắn gọn, đúng nghĩa. "
                "Chỉ trả về tiếng Nhật. Không giải thích. Không romaji. Không tiếng Việt. Không markdown."
            )
            user_prompt = (
                "Dịch sang tiếng Nhật tự nhiên:\n"
                f"Tiếng Việt: {normalized}\n"
                "Tiếng Nhật:"
            )
        else:
            return normalized

        response = chat_engine.generate_response(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_new_tokens=256,
            do_sample=False,
            temperature=0.0,
            top_p=1.0,
        )
        return self._clean_translation_response(response)

    @staticmethod
    def _clean_translation_response(text: str) -> str:
        cleaned = text.strip()
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"```$", "", cleaned).strip()
        cleaned = re.sub(
            r"^(Bản dịch sang tiếng Việt|Tiếng Việt|Vietnamese|Tiếng Nhật|Japanese)\s*:\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip()
        return cleaned

    def translate(self, request: TranslationRequest) -> TranslationResponse:
        source_lang = request.source_language.lower()
        target_lang = request.target_language.lower()

        if source_lang == "ja":
            japanese_text = request.text.strip()
            translated = self.translate_text(request.text, source_lang, target_lang)
            translation_override = translated if target_lang == "vi" else None
        elif source_lang == "vi":
            japanese_text = self.translate_text(request.text, source_lang, "ja").strip()
            translated = japanese_text
            translation_override = request.text.strip()
        else:
            japanese_text = request.text.strip()
            translated = request.text.strip()
            translation_override = None

        text_display = self.build_text_display(
            japanese_text,
            include_translation=True,
            translation_override=translation_override,
        )

        return TranslationResponse(
            source_text=request.text,
            translated_text=translated,
            source_language=source_lang,
            target_language=target_lang,
            analysis=self.build_fast_analysis(japanese_text),
            text_display=text_display,
        )

    @staticmethod
    def _katakana_to_hiragana(text: str | None) -> str | None:
        if not text:
            return text

        chars: list[str] = []
        for char in text:
            code = ord(char)
            if 0x30A1 <= code <= 0x30F6:
                chars.append(chr(code - 0x60))
            else:
                chars.append(char)
        return "".join(chars)

    @classmethod
    def _contains_kanji(cls, text: str) -> bool:
        return bool(cls._KANJI_RE.search(text))

    @classmethod
    def contains_japanese(cls, text: str) -> bool:
        return bool(text and cls._JAPANESE_CHAR_RE.search(text))

    @classmethod
    def extract_japanese_text(cls, text: str) -> str:
        if not text:
            return ""
        parts = cls._JAPANESE_CHAR_RE.findall(text)
        cleaned = " ".join(part.strip() for part in parts if part.strip())
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def tokenize_text(self, text: str) -> list[dict[str, Any]]:
        if not text.strip():
            return []
        return japanese_structure_engine.analyze(text)

    @staticmethod
    def _make_grouped_token(token: dict[str, Any]) -> dict[str, Any]:
        pos = token.get("pos") or [None]
        return {
            "surface": token.get("surface") or "",
            "reading": token.get("reading"),
            "normalized": token.get("normalized"),
            "dictionary_form": token.get("dictionary_form"),
            "pos": list(pos),
            "parts": [token],
        }

    @staticmethod
    def _is_suru_link(prev_token: dict[str, Any], token: dict[str, Any]) -> bool:
        current_dict = token.get("dictionary_form")
        current_pos = (token.get("pos") or [None])[0]
        prev_pos = (prev_token.get("pos") or [None])[0]
        return current_pos == "動詞" and current_dict in {"する", "為る"} and prev_pos in {"名詞", "動詞"}

    @staticmethod
    def _is_conjugation_continuation(prev_group: dict[str, Any], token: dict[str, Any]) -> bool:
        pos = token.get("pos") or [None, None]
        pos_main = pos[0]
        pos_sub = pos[1] if len(pos) > 1 else None
        prev_pos = (prev_group.get("pos") or [None])[0]

        if prev_pos not in {"動詞", "形容詞"}:
            return False

        if pos_main == "助詞" and pos_sub == "接続助詞" and (token.get("surface") or "") in {"て", "で"}:
            return True

        if pos_main == "動詞" and pos_sub == "非自立可能":
            return True

        if pos_main in {"助動詞", "接尾辞"}:
            return True

        return False

    @staticmethod
    def _should_attach_to_previous(prev_group: dict[str, Any] | None, token: dict[str, Any]) -> bool:
        if prev_group is None:
            return False

        pos_main = (token.get("pos") or [None])[0]
        # Keep particles and punctuation as standalone tokens so readings stay
        # aligned to actual vocabulary units instead of whole phrase chunks.
        if pos_main == "補助記号":
            return False

        if LanguageService._is_conjugation_continuation(prev_group, token):
            return True

        if pos_main == "助詞":
            return False

        if LanguageService._is_suru_link(prev_group["parts"][-1], token):
            return True

        prev_pos = (prev_group.get("pos") or [None])[0]
        if prev_pos in {"動詞", "形容詞"} and pos_main in {"助動詞", "接尾辞"}:
            return True

        return False

    def group_tokens(self, tokens: list[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped: list[dict[str, Any]] = []
        for token in tokens:
            surface = token.get("surface") or ""
            if not surface.strip():
                continue

            if self._should_attach_to_previous(grouped[-1] if grouped else None, token):
                prev = grouped[-1]
                prev["surface"] += surface
                prev["reading"] = (prev.get("reading") or "") + (token.get("reading") or "")
                prev["normalized"] = token.get("normalized") or prev.get("normalized")
                prev["dictionary_form"] = token.get("dictionary_form") or prev.get("dictionary_form")
                token_pos = list(token.get("pos") or [])
                token_main = token_pos[0] if token_pos else None
                token_sub = token_pos[1] if len(token_pos) > 1 else None
                if not (token_main == "助詞" and token_sub == "接続助詞"):
                    prev["pos"] = token_pos or prev.get("pos") or [None]
                prev["parts"].append(token)
                continue

            grouped.append(self._make_grouped_token(token))
        return grouped

    def build_text_display(
        self,
        text: str,
        *,
        include_translation: bool = True,
        include_pos: bool = True,
        translation_override: str | None = None,
    ) -> JapaneseTextDisplay:
        normalized_text = text.strip()
        if not normalized_text:
            return JapaneseTextDisplay(text="")

        tokens = self.group_tokens(self.tokenize_text(normalized_text))
        display_tokens: list[FuriganaToken] = []
        furigana_chunks: list[str] = []

        for token in tokens:
            surface = token["surface"]
            reading = self._katakana_to_hiragana(token.get("reading"))
            has_kanji = self._contains_kanji(surface)
            visible_reading = reading if has_kanji and reading and reading != surface else None

            display_tokens.append(
                FuriganaToken(
                    surface=surface,
                    reading=visible_reading,
                    has_kanji=has_kanji,
                    part_of_speech=(token.get("pos") or [None])[0] if include_pos else None,
                )
            )

            if visible_reading:
                furigana_chunks.append(f"{surface}[{visible_reading}]")
            else:
                furigana_chunks.append(surface)

        translation_vi = translation_override if include_translation else None
        if include_translation and translation_vi is None:
            translation_vi = self.translate_text(normalized_text, "ja", "vi")
        furigana_text = "".join(furigana_chunks) if furigana_chunks else normalized_text

        return JapaneseTextDisplay(
            text=normalized_text,
            translation_vi=translation_vi,
            furigana_text=furigana_text,
            tokens=display_tokens,
        )

    def build_text_displays(
        self,
        texts: list[str],
        *,
        include_translation: bool = True,
        include_pos: bool = True,
    ) -> list[JapaneseTextDisplay]:
        normalized_texts = [text.strip() for text in texts]
        translation_overrides: list[str | None] = [None] * len(normalized_texts)
        if include_translation:
            translation_overrides = self.translate_texts(normalized_texts, "ja", "vi")

        return [
            self.build_text_display(
                text,
                include_translation=include_translation,
                include_pos=include_pos,
                translation_override=translation_overrides[index] if include_translation else None,
            )
            for index, text in enumerate(normalized_texts)
        ]

    def analyze_text(
        self,
        text: str,
        *,
        include_llm: bool = True,
        include_token_translations: bool = True,
        max_vocabulary_items: int | None = None,
    ) -> TextAnalysis:
        if not text.strip():
            return TextAnalysis(summary_vi="Văn bản trống.", vocabulary=[], grammar_points=[], normalized_text="")

        tokens = self.group_tokens(self.tokenize_text(text))
        
        vocabulary = []
        for m in tokens:
            # Map Sudachi POS to internal VocabularyItem
            pos_main = m["pos"][0]
            
            if pos_main in ["助詞", "補助記号", "空白"]:
                continue

            if max_vocabulary_items is not None and len(vocabulary) >= max_vocabulary_items:
                break
                
            vocabulary.append(
                VocabularyItem(
                    surface=m["surface"],
                    reading=self._katakana_to_hiragana(m["reading"]),
                    meaning_vi=self.translate_text(m["surface"], "ja", "vi") if include_token_translations else "",
                    part_of_speech=pos_main,
                    level="N/A",
                )
            )

        # AI-powered grammar pattern detection
        grammar_points = []
        
        # OPTIMIZATION: Skip heavy LLM for single characters/kanji
        if include_llm and 1 < len(text.strip()) <= self.MAX_LLM_ANALYSIS_CHARS:
            ai_explanation = chat_engine.explain_grammar(text)
            grammar_points.append(
                GrammarPoint(
                    pattern="Phân tích ngữ pháp",
                    explanation_vi=ai_explanation,
                    example_ja=text,
                    level="AI",
                )
            )
        elif len(text.strip()) <= 1:
            # For single kanji, just provide a simple note
            grammar_points.append(
                GrammarPoint(
                    pattern="Chi tiết kanji",
                    explanation_vi=f"Đây là một chữ Kanji đơn lẻ: {text}",
                    example_ja=text,
                    level="Cơ bản",
                )
            )
        else:
            grammar_points.append(
                GrammarPoint(
                    pattern="Phân tích nhanh",
                    explanation_vi="Đã tách cụm từ, furigana và từ loại ở chế độ nhanh.",
                    example_ja=text,
                    level="Nhanh",
                )
            )

        return TextAnalysis(
            summary_vi=f"Đã phân tích {len(tokens)} thành phần ngôn ngữ.",
            vocabulary=vocabulary,
            grammar_points=grammar_points,
            normalized_text=text.strip(),
        )

    def build_fast_analysis(
        self,
        text: str,
        *,
        max_vocabulary_items: int = 16,
    ) -> TextAnalysis:
        return self.analyze_text(
            text,
            include_llm=False,
            include_token_translations=False,
            max_vocabulary_items=max_vocabulary_items,
        )

    def split_sentences(self, text: str) -> list[str]:
        normalized = text.strip()
        if not normalized:
            return []
        parts = re.split(r"(?<=[。！？!?])\s+|\n+", normalized)
        return [part.strip() for part in parts if part.strip()]

    def build_sentence_displays(self, text: str) -> list[AnalyzedSentence]:
        sentence_displays = self.build_text_displays(
            self.split_sentences(text),
            include_translation=True,
            include_pos=True,
        )
        return [
            AnalyzedSentence(
                sentence_id=index,
                text_display=display,
            )
            for index, display in enumerate(sentence_displays)
        ]

    def extract_kanji_items(self, text: str) -> list[KanjiItem]:
        seen: set[str] = set()
        results: list[KanjiItem] = []
        for char in text:
            if not self._contains_kanji(char) or char in seen:
                continue
            seen.add(char)
            metadata = kanji_engine._load_kanji_metadata(char)
            reading = None
            meaning_vi = None
            if metadata:
                reading = ", ".join((metadata.get("reading") or {}).get("kun") or []) or None
                if not reading:
                    reading = ", ".join((metadata.get("reading") or {}).get("on") or []) or None
                meaning_vi = ((metadata.get("meaning") or {}).get("vi") or None)
            results.append(KanjiItem(kanji=char, reading=reading, meaning_vi=meaning_vi))
        return results

    def translate_text(self, text: str, source_language: str = "ja", target_language: str = "vi") -> str:
        normalized = text.strip()
        if not normalized:
            return ""

        cache_key = (source_language, target_language, normalized)
        cached = self._translation_cache.get(cache_key)
        if cached is not None:
            return cached

        if (
            source_language == "ja" and target_language == "vi"
        ) or (
            source_language == "vi" and target_language == "ja"
        ):
            cleaned = self._translate_with_chat(normalized, source_language, target_language)
            self._translation_cache[cache_key] = cleaned
            return cleaned

        return normalized

    def translate_texts(
        self,
        texts: list[str],
        source_language: str = "ja",
        target_language: str = "vi",
    ) -> list[str]:
        normalized_texts = [text.strip() for text in texts]
        results = [""] * len(normalized_texts)

        if (
            source_language != "ja" or target_language != "vi"
        ) and (
            source_language != "vi" or target_language != "ja"
        ):
            return [self.translate_text(text, source_language, target_language) for text in normalized_texts]

        uncached_indexes: list[int] = []
        uncached_texts: list[str] = []

        for index, normalized in enumerate(normalized_texts):
            if not normalized:
                continue
            cache_key = (source_language, target_language, normalized)
            cached = self._translation_cache.get(cache_key)
            if cached is not None:
                results[index] = cached
                continue
            uncached_indexes.append(index)
            uncached_texts.append(normalized)

        if uncached_texts:
            for index, normalized in zip(uncached_indexes, uncached_texts):
                cleaned = self._translate_with_chat(normalized, source_language, target_language)
                cache_key = (source_language, target_language, normalized_texts[index])
                self._translation_cache[cache_key] = cleaned
                results[index] = cleaned

        return results


language_service = LanguageService()
