from typing import List, Optional
from pydantic import BaseModel

class TextBlock(BaseModel):
    text: str
    confidence: float
    box: List[List[float]]

class OCRResponse(BaseModel):
    full_text: str
    blocks: List[TextBlock]
    image_url: Optional[str] = None
