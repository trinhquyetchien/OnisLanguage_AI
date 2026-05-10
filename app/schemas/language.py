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


class TranslationResponse(BaseModel):
    source_text: str
    translated_text: str
    source_language: LanguageCode
    target_language: LanguageCode
    analysis: TextAnalysis


class AnalyzeTextRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    language: LanguageCode = "ja"


class AnalyzeTextResponse(BaseModel):
    text: str
    language: LanguageCode
    analysis: TextAnalysis
