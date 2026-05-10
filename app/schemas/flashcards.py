from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class FlashcardBase(BaseModel):
    front: str
    back: str
    example_sentence: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class FlashcardCreateRequest(FlashcardBase):
    pass


class FlashcardUpdateRequest(BaseModel):
    front: Optional[str] = None
    back: Optional[str] = None
    example_sentence: Optional[str] = None
    tags: Optional[List[str]] = None


class FlashcardResponse(FlashcardBase):
    card_id: str


class FlashcardDeckCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    language_focus: str = "Japanese"


class FlashcardDeckResponse(BaseModel):
    deck_id: str
    title: str
    description: Optional[str] = None
    language_focus: str = "Japanese"
    cards: List[FlashcardResponse] = Field(default_factory=list)
