from typing import List, Optional
from pydantic import BaseModel

class TranscriptSegment(BaseModel):
    segment_id: int
    start: float
    end: float
    text_ja: str

class TranscriptionResponse(BaseModel):
    full_text_ja: str
    segments: List[TranscriptSegment]
    duration: float
    media_url: Optional[str] = None
    media_kind: Optional[str] = None
    audio_filename: Optional[str] = None
