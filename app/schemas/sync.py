from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


SyncEntityType = Literal[
    "user_profile",
    "flashcard_deck",
    "flashcard",
    "flashcard_review",
    "practice_exam",
    "practice_question",
    "practice_submission",
]

SyncOperation = Literal["upsert", "delete"]


class SyncChange(BaseModel):
    entity_type: SyncEntityType
    entity_id: str
    operation: SyncOperation = "upsert"
    payload: Dict[str, Any] = Field(default_factory=dict)
    client_updated_at: Optional[datetime] = None


class SyncPushRequest(BaseModel):
    user_id: str
    device_id: str
    changes: List[SyncChange] = Field(default_factory=list)


class SyncEvent(BaseModel):
    event_id: int
    entity_type: SyncEntityType
    entity_id: str
    operation: SyncOperation
    payload: Dict[str, Any] = Field(default_factory=dict)
    server_updated_at: datetime


class SyncPushResponse(BaseModel):
    accepted: int
    latest_cursor: int
    events: List[SyncEvent] = Field(default_factory=list)


class SyncPullResponse(BaseModel):
    latest_cursor: int
    events: List[SyncEvent] = Field(default_factory=list)


class SyncSnapshotResponse(BaseModel):
    user_id: str
    latest_cursor: int
    decks: List[Dict[str, Any]] = Field(default_factory=list)
    cards: List[Dict[str, Any]] = Field(default_factory=list)
    exams: List[Dict[str, Any]] = Field(default_factory=list)
    submissions: List[Dict[str, Any]] = Field(default_factory=list)
