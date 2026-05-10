from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.language import TextAnalysis


class TextBlock(BaseModel):
    text: str
    confidence: float
    box: List[List[float]]


class OCRResponse(BaseModel):
    full_text: str
    translated_text_vi: Optional[str] = None
    analysis: Optional[TextAnalysis] = None
    blocks: List[TextBlock] = Field(default_factory=list)
    image_url: Optional[str] = None


class TranscriptSegment(BaseModel):
    segment_id: int
    start: float
    end: float
    text_ja: str
    text_vi: Optional[str] = None


class TranscriptionResponse(BaseModel):
    full_text_ja: str
    full_text_vi: Optional[str] = None
    analysis: Optional[TextAnalysis] = None
    segments: List[TranscriptSegment] = Field(default_factory=list)
    duration: float
    media_url: Optional[str] = None
    media_kind: Optional[str] = None
    audio_filename: Optional[str] = None


class KanjiPrediction(BaseModel):
    kanji: str
    confidence: float
    label_id: int
    meaning_vi: Optional[str] = None
    reading: Optional[str] = None
    analysis: Optional[TextAnalysis] = None


class KanjiResponse(BaseModel):
    top1: KanjiPrediction
    top5: List[KanjiPrediction] = Field(default_factory=list)
