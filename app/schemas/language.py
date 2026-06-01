from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field


LanguageCode = Literal["ja", "vi"]


class TranslationRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    source_language: LanguageCode = "ja"
    target_language: LanguageCode = "vi"


class VocabularyItem(BaseModel):
    surface: str
    reading: str | None = None
    meaning_vi: str
    part_of_speech: str | None = None
    level: str | None = None


class GrammarPoint(BaseModel):
    pattern: str
    explanation_vi: str
    example_ja: str | None = None
    level: str | None = None


class TextAnalysis(BaseModel):
    summary_vi: str
    vocabulary: List[VocabularyItem] = Field(default_factory=list)
    grammar_points: List[GrammarPoint] = Field(default_factory=list)
    normalized_text: str


class FuriganaToken(BaseModel):
    surface: str
    reading: str | None = None
    has_kanji: bool = False
    part_of_speech: str | None = None


class JapaneseTextDisplay(BaseModel):
    text: str
    translation_vi: str | None = None
    furigana_text: str | None = None
    tokens: List[FuriganaToken] = Field(default_factory=list)


class KanjiItem(BaseModel):
    kanji: str
    reading: str | None = None
    meaning_vi: str | None = None


class AnalyzedSentence(BaseModel):
    sentence_id: int
    text_display: JapaneseTextDisplay


class TranslationResponse(BaseModel):
    source_text: str
    translated_text: str
    source_language: LanguageCode
    target_language: LanguageCode
    analysis: TextAnalysis
    text_display: JapaneseTextDisplay | None = None


class AnalyzeTextRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    language: LanguageCode = "ja"


class AnalyzeTextResponse(BaseModel):
    text: str
    language: LanguageCode
    normalized_text: str
    sentences: List[AnalyzedSentence] = Field(default_factory=list)
    analysis: TextAnalysis
    kanji: List[KanjiItem] = Field(default_factory=list)
