from typing import List
from pydantic import BaseModel

class KanjiPrediction(BaseModel):
    kanji: str
    confidence: float
    label_id: int

class KanjiResponse(BaseModel):
    top1: KanjiPrediction
    top5: List[KanjiPrediction]
