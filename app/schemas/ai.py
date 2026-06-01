from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.language import AnalyzedSentence, JapaneseTextDisplay, TextAnalysis


class TextBlock(BaseModel):
    text: str
    confidence: float
    box: List[List[float]]


class OCRResponse(BaseModel):
    full_text: str
    translated_text_vi: Optional[str] = None
    text_display: Optional[JapaneseTextDisplay] = None
    sentences: List[AnalyzedSentence] = Field(default_factory=list)
    analysis: Optional[TextAnalysis] = None
    blocks: List[TextBlock] = Field(default_factory=list)
    image_url: Optional[str] = None


class TranscriptWord(BaseModel):
    start: float
    end: float
    text_ja: str
    confidence: Optional[float] = None
    text_display: Optional[JapaneseTextDisplay] = None


class TranscriptSegment(BaseModel):
    segment_id: int
    start: float
    end: float
    text_ja: str
    text_vi: Optional[str] = None
    text_display: Optional[JapaneseTextDisplay] = None
    words: List[TranscriptWord] = Field(default_factory=list)


class TranscriptionResponse(BaseModel):
    full_text_ja: str
    full_text_vi: Optional[str] = None
    text_display: Optional[JapaneseTextDisplay] = None
    analysis: Optional[TextAnalysis] = None
    segments: List[TranscriptSegment] = Field(default_factory=list)
    duration: float
    media_url: Optional[str] = None
    media_kind: Optional[str] = None
    media_title: Optional[str] = None
    audio_filename: Optional[str] = None


class MediaTranscriptHistoryResponse(BaseModel):
    history_id: int
    title: str
    source_type: str
    source_uri: Optional[str] = None
    media_url: Optional[str] = None
    media_kind: Optional[str] = None
    duration: float
    full_text_ja: str
    full_text_vi: Optional[str] = None
    text_display: Optional[JapaneseTextDisplay] = None
    segments: List[TranscriptSegment] = Field(default_factory=list)
    created_at: datetime


class KanjiPrediction(BaseModel):
    kanji: str
    confidence: float
    label_id: int
    meaning_vi: Optional[str] = None
    reading: Optional[str] = None
    analysis: Optional[TextAnalysis] = None
    details: Optional["KanjiDetails"] = None


class KanjiComment(BaseModel):
    content_text: str
    image_url: Optional[str] = None
    user_name: Optional[str] = None


class KanjiDetails(BaseModel):
    meaning_vi: Optional[str] = None
    meaning_en: Optional[str] = None
    on_readings: List[str] = Field(default_factory=list)
    kun_readings: List[str] = Field(default_factory=list)
    am_han: Optional[str] = None
    stroke_count: Optional[int] = None
    frequency: Optional[int] = None
    examples: List[str] = Field(default_factory=list)
    explanation: Optional[str] = None
    svg_url: Optional[str] = None
    image_urls: List[str] = Field(default_factory=list)
    comments: List[KanjiComment] = Field(default_factory=list)


class KanjiResponse(BaseModel):
    top1: KanjiPrediction
    top5: List[KanjiPrediction] = Field(default_factory=list)


KanjiPrediction.model_rebuild()
