from pydantic import BaseModel, Field


class TranscriptSegment(BaseModel):
    segment_id: int
    start: float
    end: float
    text_ja: str


class TranscriptResponse(BaseModel):
    audio_filename: str
    duration: float
    full_text_ja: str
    segments: list[TranscriptSegment]
    media_url: str = Field(..., description="Relative URL for playback.")
    media_kind: str = Field(..., description="Either `audio` or `video`.")


class HealthResponse(BaseModel):
    status: str
    model_path: str
