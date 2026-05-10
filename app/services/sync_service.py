from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from app.schemas.sync import SyncEvent, SyncPullResponse, SyncPushRequest, SyncPushResponse, SyncSnapshotResponse


class SyncService:
    def __init__(self) -> None:
        self._next_event_id = 1
        self._events_by_user: dict[str, list[SyncEvent]] = {}
        self._entities_by_user: dict[str, dict[str, dict[str, Any]]] = {}

    def push(self, request: SyncPushRequest) -> SyncPushResponse:
        accepted_events: List[SyncEvent] = []
        user_events = self._events_by_user.setdefault(request.user_id, [])
        user_entities = self._entities_by_user.setdefault(request.user_id, {})

        for change in request.changes:
            event = SyncEvent(
                event_id=self._next_event_id,
                entity_type=change.entity_type,
                entity_id=change.entity_id,
                operation=change.operation,
                payload=change.payload,
                server_updated_at=datetime.now(timezone.utc),
            )
            self._next_event_id += 1
            user_events.append(event)
            accepted_events.append(event)

            entity_key = f"{change.entity_type}:{change.entity_id}"
            if change.operation == "delete":
                user_entities.pop(entity_key, None)
            else:
                user_entities[entity_key] = {
                    "entity_type": change.entity_type,
                    "entity_id": change.entity_id,
                    **change.payload,
                    "server_updated_at": event.server_updated_at.isoformat(),
                }

        latest_cursor = user_events[-1].event_id if user_events else 0
        return SyncPushResponse(accepted=len(accepted_events), latest_cursor=latest_cursor, events=accepted_events)

    def pull(self, user_id: str, since: int = 0) -> SyncPullResponse:
        events = [event for event in self._events_by_user.get(user_id, []) if event.event_id > since]
        latest_cursor = max([since, *[event.event_id for event in events]], default=since)
        return SyncPullResponse(latest_cursor=latest_cursor, events=events)

    def snapshot(self, user_id: str) -> SyncSnapshotResponse:
        entities = list(self._entities_by_user.get(user_id, {}).values())
        latest_cursor = self._events_by_user.get(user_id, [])[-1].event_id if self._events_by_user.get(user_id) else 0
        return SyncSnapshotResponse(
            user_id=user_id,
            latest_cursor=latest_cursor,
            decks=[item for item in entities if item["entity_type"] == "flashcard_deck"],
            cards=[item for item in entities if item["entity_type"] == "flashcard"],
            exams=[item for item in entities if item["entity_type"] == "practice_exam"],
            submissions=[item for item in entities if item["entity_type"] == "practice_submission"],
        )


sync_service = SyncService()
