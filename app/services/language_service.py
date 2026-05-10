from __future__ import annotations

import re

from app.schemas.language import (
    GrammarPoint,
    TextAnalysis,
    TranslationRequest,
    TranslationResponse,
    VocabularyItem,
)


class LanguageService:
    _ja_vi_dictionary = {
        "こんにちは": ("Xin chào", "konnichiwa", "greeting", "n5"),
        "ありがとう": ("Cảm ơn", "arigatou", "greeting", "n5"),
        "日本": ("Nhật Bản", "nihon", "noun", "n5"),
        "日本語": ("tiếng Nhật", "nihongo", "noun", "n5"),
        "勉強": ("học tập", "benkyou", "noun/verb", "n5"),
        "学生": ("học sinh", "gakusei", "noun", "n5"),
        "先生": ("giáo viên", "sensei", "noun", "n5"),
        "学校": ("trường học", "gakkou", "noun", "n5"),
        "水": ("nước", "mizu", "noun", "n5"),
        "食べる": ("ăn", "taberu", "verb", "n5"),
        "行く": ("đi", "iku", "verb", "n5"),
        "見る": ("xem/nhìn", "miru", "verb", "n5"),
        "海": ("biển", "umi", "noun", "n5"),
        "山": ("núi", "yama", "noun", "n5"),
        "富士山": ("núi Phú Sĩ", "fujisan", "noun", "n4"),
    }

    _vi_ja_dictionary = {
        "xin chào": "こんにちは",
        "cảm ơn": "ありがとう",
        "nhật bản": "日本",
        "tiếng nhật": "日本語",
        "học tập": "勉強",
        "học sinh": "学生",
        "giáo viên": "先生",
        "trường học": "学校",
        "nước": "水",
        "ăn": "食べる",
        "đi": "行く",
        "xem": "見る",
        "biển": "海",
        "núi": "山",
    }

    def translate(self, request: TranslationRequest) -> TranslationResponse:
        source_lang = request.source_language.lower()
        target_lang = request.target_language.lower()
        
        translated = self.translate_text(request.text, source_lang, target_lang)
        
        return TranslationResponse(
            source_text=request.text,
            translated_text=translated,
            source_language=source_lang,
            target_language=target_lang,
            analysis=self.analyze_text(request.text if source_lang == "ja" else translated),
        )

    def analyze_text(self, text: str) -> TextAnalysis:
        vocabulary = []
        for surface, (meaning, reading, pos, level) in self._ja_vi_dictionary.items():
            if surface in text:
                vocabulary.append(
                    VocabularyItem(
                        surface=surface,
                        reading=reading,
                        meaning_vi=meaning,
                        part_of_speech=pos,
                        level=level,
                    )
                )

        grammar_points = []
        if "です" in text:
            grammar_points.append(
                GrammarPoint(
                    pattern="N/Adj + です",
                    explanation_vi="Mẫu câu lịch sự dùng để khẳng định hoặc mô tả.",
                    example_ja="今日はいい天気です。",
                    level="n5",
                )
            )
        if "ませんか" in text:
            grammar_points.append(
                GrammarPoint(
                    pattern="Vませんか",
                    explanation_vi="Mẫu câu rủ rê/lời mời lịch sự: bạn có muốn ... không?",
                    example_ja="一緒に行きませんか。",
                    level="n5",
                )
            )

        summary = "Đã phân tích văn bản tiếng Nhật và trích xuất từ vựng/ngữ pháp chính."
        if not vocabulary and not grammar_points:
            summary = "Chưa tìm thấy mục từ/ngữ pháp trong bộ phân tích mẫu."

        return TextAnalysis(
            summary_vi=summary,
            vocabulary=vocabulary,
            grammar_points=grammar_points,
            normalized_text=text.strip(),
        )

    def translate_text(self, text: str, source_language: str = "ja", target_language: str = "vi") -> str:
        if source_language == "ja" and target_language == "vi":
            return self._translate_ja_to_vi(text)
        if source_language == "vi" and target_language == "ja":
            return self._translate_vi_to_ja(text)
        return text

    def _translate_ja_to_vi(self, text: str) -> str:
        translated = text
        for surface, (meaning, _, _, _) in sorted(self._ja_vi_dictionary.items(), key=lambda item: len(item[0]), reverse=True):
            translated = translated.replace(surface, meaning)
        translated = translated.replace("。", ".").replace("、", ", ")
        return translated

    def _translate_vi_to_ja(self, text: str) -> str:
        translated = text.lower()
        for surface, ja in sorted(self._vi_ja_dictionary.items(), key=lambda item: len(item[0]), reverse=True):
            translated = re.sub(re.escape(surface), ja, translated, flags=re.IGNORECASE)
        return translated


language_service = LanguageService()
