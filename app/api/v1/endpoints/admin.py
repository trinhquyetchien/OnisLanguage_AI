from __future__ import annotations

import json
import math
import re
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Float, Integer, String, Text, cast, func, or_
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Session

from app.api import deps
from app.admin.router import TABLES
from app.db.models import Flashcard, FlashcardDeck, MediaTranscriptHistory, PracticeExam, PracticeQuestion, User

router = APIRouter()
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
COLLECTION_KEYS = {"users", "flashcards", "exams"}


def _require_admin(current_user: User = Depends(deps.get_current_user)) -> User:
    allowed = {email.lower() for email in deps.settings.ADMIN_EMAILS}
    if "*" not in allowed and current_user.email.lower() not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


def _serialize_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _preview_value(value: Any) -> str:
    if isinstance(value, (list, dict)):
        text = json.dumps(value, ensure_ascii=False)
    else:
        text = "" if value is None else str(value)
    compact = " ".join(text.split())
    return compact[:117] + "..." if len(compact) > 120 else compact


def _column_input_type(column: Any) -> str:
    column_type = column.type
    if isinstance(column_type, (Integer, Float)):
        return "number"
    if isinstance(column_type, JSONB):
        return "json"
    if isinstance(column_type, ARRAY):
        return "array"
    if isinstance(column_type, Text):
        return "textarea"
    return "text"


def _coerce_value(column: Any, raw: Any, *, is_create: bool) -> Any:
    if raw is None:
        return None
    if isinstance(raw, str):
        raw = raw.strip()
    if raw == "":
        if column.primary_key and is_create:
            return None
        return None

    column_type = column.type
    if isinstance(column_type, Integer):
        return int(raw)
    if isinstance(column_type, Float):
        return float(raw)
    if isinstance(column_type, UUID):
        return str(raw)
    if isinstance(column_type, JSONB):
        return raw if isinstance(raw, (dict, list)) else json.loads(raw)
    if isinstance(column_type, ARRAY):
        if isinstance(raw, list):
            return raw
        if isinstance(raw, str) and raw.startswith("["):
            return json.loads(raw)
        return [item.strip() for item in str(raw).replace("\r", "").split("\n") if item.strip()]
    return raw


def _record_to_dict(table_key: str, record: Any) -> dict[str, Any]:
    table = TABLES[table_key]
    data = {}
    preview = {}
    for column in table.model.__table__.columns:
        value = getattr(record, column.name)
        data[column.name] = _serialize_value(value)
        preview[column.name] = _preview_value(value)
    return {
        "id": str(getattr(record, table.primary_key)),
        "table": table_key,
        "data": data,
        "preview": preview,
    }


def _schema_for_table(table_key: str) -> dict[str, Any]:
    table = TABLES[table_key]
    fields = []
    for column in table.model.__table__.columns:
        fields.append(
            {
                "name": column.name,
                "label": column.name.replace("_", " ").title(),
                "required": not column.nullable and column.default is None and column.server_default is None and not column.primary_key,
                "readonly_on_edit": bool(column.primary_key),
                "primary_key": bool(column.primary_key),
                "type": _column_input_type(column),
                "db_type": str(column.type),
            }
        )
    if table_key == "users":
        fields.append(
            {
                "name": "raw_password",
                "label": "Raw Password",
                "required": False,
                "readonly_on_edit": False,
                "primary_key": False,
                "type": "password",
                "db_type": "password",
            }
        )
    return {
        "key": table.key,
        "label": table.label,
        "description": table.description,
        "primary_key": table.primary_key,
        "accent": table.accent,
        "fields": fields,
    }


def _query_for_table(db: Session, table_key: str, q: str | None):
    table = TABLES[table_key]
    query = db.query(table.model)
    if q:
        clauses = []
        for column in table.model.__table__.columns:
            if isinstance(column.type, (String, Text, UUID)):
                clauses.append(cast(column, String).ilike(f"%{q}%"))
        if clauses:
            query = query.filter(or_(*clauses))
    return query


def _validate_payload(table_key: str, payload: dict[str, Any], *, is_create: bool) -> dict[str, Any]:
    table = TABLES[table_key]
    allowed_fields = {column.name: column for column in table.model.__table__.columns}
    if table_key == "users":
        allowed_fields["raw_password"] = None

    unknown = sorted(key for key in payload.keys() if key not in allowed_fields)
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown fields: {', '.join(unknown)}")

    values: dict[str, Any] = {}
    errors: list[str] = []
    for column in table.model.__table__.columns:
        if column.name not in payload:
            continue
        if not is_create and column.primary_key:
            continue
        try:
            values[column.name] = _coerce_value(column, payload[column.name], is_create=is_create)
        except Exception as exc:
            errors.append(f"{column.name}: {exc}")

    for column in table.model.__table__.columns:
        required = not column.nullable and column.default is None and column.server_default is None and not column.primary_key
        if required and is_create and values.get(column.name) in (None, ""):
            if table_key == "users" and column.name == "password_hash":
                continue
            errors.append(f"{column.name}: field is required")

    if table_key == "users":
        email = values.get("email")
        if email not in (None, ""):
            normalized_email = str(email).strip().lower()
            if not EMAIL_RE.match(normalized_email):
                errors.append("email: invalid email format")
            values["email"] = normalized_email

        raw_password = payload.get("raw_password")
        if raw_password not in (None, "") and len(str(raw_password)) < 6:
            errors.append("raw_password: minimum 6 characters")

        if is_create and not raw_password and values.get("password_hash") in (None, ""):
            errors.append("raw_password or password_hash is required")

    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))
    return values


def _parse_date_param(raw: str | None, field_name: str) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"{field_name} must be YYYY-MM-DD") from exc


def _normalize_granularity(raw: str | None) -> str:
    value = (raw or "day").strip().lower()
    if value not in {"day", "week", "month", "year"}:
        raise HTTPException(status_code=400, detail="granularity must be one of: day, week, month, year")
    return value


def _month_start(value: date) -> date:
    return value.replace(day=1)


def _year_start(value: date) -> date:
    return value.replace(month=1, day=1)


def _align_bucket_start(value: date, granularity: str) -> date:
    if granularity == "week":
        return value - timedelta(days=value.weekday())
    if granularity == "month":
        return _month_start(value)
    if granularity == "year":
        return _year_start(value)
    return value


def _add_months(value: date, delta: int) -> date:
    year = value.year + ((value.month - 1 + delta) // 12)
    month = ((value.month - 1 + delta) % 12) + 1
    return date(year, month, 1)


def _add_years(value: date, delta: int) -> date:
    return date(value.year + delta, 1, 1)


def _next_bucket(value: date, granularity: str) -> date:
    if granularity == "day":
        return value + timedelta(days=1)
    if granularity == "week":
        return value + timedelta(weeks=1)
    if granularity == "month":
        return _add_months(value, 1)
    return _add_years(value, 1)


def _default_window_end() -> date:
    return datetime.now(timezone.utc).date()


def _default_window_start(end_value: date, granularity: str) -> date:
    if granularity == "day":
        return end_value - timedelta(days=29)
    if granularity == "week":
        return end_value - timedelta(weeks=11)
    if granularity == "month":
        return _add_months(_month_start(end_value), -11)
    return date(end_value.year - 4, 1, 1)


def _resolve_window(start_raw: str | None, end_raw: str | None, granularity_raw: str | None) -> tuple[str, date, date, datetime, datetime]:
    granularity = _normalize_granularity(granularity_raw)
    end_date = _parse_date_param(end_raw, "end_date") or _default_window_end()
    start_date = _parse_date_param(start_raw, "start_date") or _default_window_start(end_date, granularity)

    start_date = _align_bucket_start(start_date, granularity)
    end_date = _align_bucket_start(end_date, granularity)
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date must be greater than or equal to start_date")

    start_dt = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    end_exclusive = datetime.combine(_next_bucket(end_date, granularity), time.min, tzinfo=timezone.utc)
    return granularity, start_date, end_date, start_dt, end_exclusive


def _bucket_label(value: date, granularity: str) -> str:
    if granularity == "day":
        return value.strftime("%d/%m")
    if granularity == "week":
        return value.strftime("W%W • %d/%m")
    if granularity == "month":
        return value.strftime("%m/%Y")
    return value.strftime("%Y")


def _build_series_map(rows: list[tuple[Any, int]], granularity: str) -> dict[date, int]:
    result: dict[date, int] = {}
    for bucket, count in rows:
        if isinstance(bucket, datetime):
            bucket_date = bucket.date()
        elif isinstance(bucket, date):
            bucket_date = bucket
        else:
            continue
        result[_align_bucket_start(bucket_date, granularity)] = int(count or 0)
    return result


def _series_from_rows(rows: list[tuple[Any, int]], start_date: date, end_date: date, granularity: str) -> list[dict[str, Any]]:
    values = _build_series_map(rows, granularity)
    current = start_date
    points: list[dict[str, Any]] = []
    while current <= end_date:
        points.append(
            {
                "bucket": current.isoformat(),
                "label": _bucket_label(current, granularity),
                "value": values.get(current, 0),
            }
        )
        current = _next_bucket(current, granularity)
    return points


def _count_series(
    db: Session,
    model: Any,
    *,
    start_dt: datetime,
    end_exclusive: datetime,
    granularity: str,
) -> list[tuple[Any, int]]:
    bucket = func.date_trunc(granularity, model.created_at)
    return (
        db.query(bucket.label("bucket"), func.count().label("count"))
        .filter(model.created_at >= start_dt, model.created_at < end_exclusive)
        .group_by(bucket)
        .order_by(bucket.asc())
        .all()
    )


def _safe_count(value: Any) -> int:
    return int(value or 0)


def _recent_payload(table_key: str, records: list[Any]) -> list[dict[str, Any]]:
    return [_record_to_dict(table_key, item) for item in records]


def _user_admin_count(db: Session) -> int:
    allowed = [email.lower() for email in deps.settings.ADMIN_EMAILS if email != "*"]
    if not allowed:
        return 0
    return _safe_count(db.query(func.count(User.user_id)).filter(func.lower(User.email).in_(allowed)).scalar())


def _dashboard_payload(db: Session, current_user: User, *, start_raw: str | None, end_raw: str | None, granularity_raw: str | None) -> dict[str, Any]:
    granularity, start_date, end_date, start_dt, end_exclusive = _resolve_window(start_raw, end_raw, granularity_raw)

    total_users = _safe_count(db.query(func.count(User.user_id)).scalar())
    total_flashcard_decks = _safe_count(db.query(func.count(FlashcardDeck.deck_id)).scalar())
    total_flashcards = _safe_count(db.query(func.count(Flashcard.card_id)).scalar())
    total_exams = _safe_count(db.query(func.count(PracticeExam.exam_id)).scalar())
    total_questions = _safe_count(db.query(func.count(PracticeQuestion.question_id)).scalar())
    total_media_runs = _safe_count(db.query(func.count(MediaTranscriptHistory.history_id)).scalar())

    new_users = _safe_count(
        db.query(func.count(User.user_id))
        .filter(User.created_at >= start_dt, User.created_at < end_exclusive)
        .scalar()
    )
    new_decks = _safe_count(
        db.query(func.count(FlashcardDeck.deck_id))
        .filter(FlashcardDeck.created_at >= start_dt, FlashcardDeck.created_at < end_exclusive)
        .scalar()
    )
    new_exams = _safe_count(
        db.query(func.count(PracticeExam.exam_id))
        .filter(PracticeExam.created_at >= start_dt, PracticeExam.created_at < end_exclusive)
        .scalar()
    )
    media_runs_in_range = _safe_count(
        db.query(func.count(MediaTranscriptHistory.history_id))
        .filter(MediaTranscriptHistory.created_at >= start_dt, MediaTranscriptHistory.created_at < end_exclusive)
        .scalar()
    )

    user_series = _series_from_rows(
        _count_series(db, User, start_dt=start_dt, end_exclusive=end_exclusive, granularity=granularity),
        start_date,
        end_date,
        granularity,
    )
    deck_series = _series_from_rows(
        _count_series(db, FlashcardDeck, start_dt=start_dt, end_exclusive=end_exclusive, granularity=granularity),
        start_date,
        end_date,
        granularity,
    )
    exam_series = _series_from_rows(
        _count_series(db, PracticeExam, start_dt=start_dt, end_exclusive=end_exclusive, granularity=granularity),
        start_date,
        end_date,
        granularity,
    )
    media_series = _series_from_rows(
        _count_series(db, MediaTranscriptHistory, start_dt=start_dt, end_exclusive=end_exclusive, granularity=granularity),
        start_date,
        end_date,
        granularity,
    )

    activity_series = []
    for index, point in enumerate(user_series):
        activity_series.append(
            {
                "bucket": point["bucket"],
                "label": point["label"],
                "users": point["value"],
                "decks": deck_series[index]["value"],
                "exams": exam_series[index]["value"],
                "media": media_series[index]["value"],
            }
        )

    feature_usage = [
        {"key": "users", "label": "Đăng ký", "value": new_users, "accent": "#0f766e"},
        {"key": "flashcards", "label": "Flashcards", "value": new_decks, "accent": "#2563eb"},
        {"key": "exams", "label": "Đề thi", "value": new_exams, "accent": "#d97706"},
        {"key": "media", "label": "AI / Media", "value": media_runs_in_range, "accent": "#7c3aed"},
    ]

    media_type_rows = (
        db.query(MediaTranscriptHistory.source_type, func.count(MediaTranscriptHistory.history_id))
        .filter(MediaTranscriptHistory.created_at >= start_dt, MediaTranscriptHistory.created_at < end_exclusive)
        .group_by(MediaTranscriptHistory.source_type)
        .order_by(func.count(MediaTranscriptHistory.history_id).desc())
        .all()
    )
    media_breakdown = [
        {
            "label": source_type or "unknown",
            "value": _safe_count(count),
        }
        for source_type, count in media_type_rows
    ]

    recent_users = db.query(User).order_by(User.created_at.desc()).limit(6).all()
    recent_exams = db.query(PracticeExam).order_by(PracticeExam.created_at.desc()).limit(6).all()
    recent_media = db.query(MediaTranscriptHistory).order_by(MediaTranscriptHistory.created_at.desc()).limit(6).all()

    return {
        "filters": {
            "granularity": granularity,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "summary": {
            "admin_email": current_user.email,
            "total_users": total_users,
            "total_flashcard_decks": total_flashcard_decks,
            "total_flashcards": total_flashcards,
            "total_exams": total_exams,
            "total_questions": total_questions,
            "total_media_runs": total_media_runs,
            "new_users": new_users,
            "new_decks": new_decks,
            "new_exams": new_exams,
            "media_runs_in_range": media_runs_in_range,
            "admin_eligible_users": _user_admin_count(db),
        },
        "registration_series": user_series,
        "activity_series": activity_series,
        "feature_usage": feature_usage,
        "media_breakdown": media_breakdown,
        "recent_users": _recent_payload("users", recent_users),
        "recent_exams": _recent_payload("practice_exams", recent_exams),
        "recent_media": _recent_payload("media_transcript_history", recent_media),
    }


def _paginate(page: int, page_size: int, total: int) -> dict[str, Any]:
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": max(math.ceil(total / page_size), 1),
    }


def _collection_payload(
    db: Session,
    *,
    collection_key: str,
    q: str | None,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    search = (q or "").strip()

    if collection_key == "users":
        query = db.query(User)
        if search:
            query = query.filter(
                or_(
                    User.email.ilike(f"%{search}%"),
                    User.display_name.ilike(f"%{search}%"),
                )
            )
        total = _safe_count(query.count())
        items = query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
        summary = {
            "total_users": _safe_count(db.query(func.count(User.user_id)).scalar()),
            "new_last_7_days": _safe_count(
                db.query(func.count(User.user_id))
                .filter(User.created_at >= datetime.now(timezone.utc) - timedelta(days=7))
                .scalar()
            ),
            "new_last_30_days": _safe_count(
                db.query(func.count(User.user_id))
                .filter(User.created_at >= datetime.now(timezone.utc) - timedelta(days=30))
                .scalar()
            ),
            "admin_eligible_users": _user_admin_count(db),
        }
        return {
            "collection": "users",
            "summary": summary,
            "items": [_record_to_dict("users", item) for item in items],
            "pagination": {**_paginate(page, page_size, total), "query": search},
        }

    if collection_key == "flashcards":
        card_counts = (
            db.query(Flashcard.deck_id.label("deck_id"), func.count(Flashcard.card_id).label("cards_count"))
            .group_by(Flashcard.deck_id)
            .subquery()
        )
        query = (
            db.query(
                FlashcardDeck,
                User.display_name.label("owner_name"),
                User.email.label("owner_email"),
                func.coalesce(card_counts.c.cards_count, 0).label("cards_count"),
            )
            .outerjoin(User, FlashcardDeck.owner_user_id == User.user_id)
            .outerjoin(card_counts, FlashcardDeck.deck_id == card_counts.c.deck_id)
        )
        if search:
            query = query.filter(
                or_(
                    FlashcardDeck.title.ilike(f"%{search}%"),
                    FlashcardDeck.description.ilike(f"%{search}%"),
                    FlashcardDeck.language_focus.ilike(f"%{search}%"),
                    User.display_name.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%"),
                )
            )
        total = _safe_count(query.count())
        rows = query.order_by(FlashcardDeck.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
        summary = {
            "total_decks": _safe_count(db.query(func.count(FlashcardDeck.deck_id)).scalar()),
            "total_cards": _safe_count(db.query(func.count(Flashcard.card_id)).scalar()),
            "public_decks": _safe_count(db.query(func.count(FlashcardDeck.deck_id)).filter(FlashcardDeck.visibility == "public").scalar()),
            "decks_with_owner": _safe_count(db.query(func.count(FlashcardDeck.deck_id)).filter(FlashcardDeck.owner_user_id.isnot(None)).scalar()),
        }
        items = []
        for deck, owner_name, owner_email, cards_count in rows:
            items.append(
                {
                    "id": str(deck.deck_id),
                    "table": "flashcard_decks",
                    "data": {
                        "deck_id": str(deck.deck_id),
                        "title": deck.title,
                        "description": deck.description,
                        "language_focus": deck.language_focus,
                        "visibility": deck.visibility,
                        "tags": deck.tags or [],
                        "owner_user_id": str(deck.owner_user_id) if deck.owner_user_id else None,
                        "owner_name": owner_name,
                        "owner_email": owner_email,
                        "cards_count": _safe_count(cards_count),
                        "created_at": deck.created_at.isoformat() if deck.created_at else None,
                    },
                }
            )
        return {
            "collection": "flashcards",
            "summary": summary,
            "items": items,
            "pagination": {**_paginate(page, page_size, total), "query": search},
        }

    if collection_key == "exams":
        question_counts = (
            db.query(PracticeQuestion.exam_id.label("exam_id"), func.count(PracticeQuestion.question_id).label("question_count"))
            .group_by(PracticeQuestion.exam_id)
            .subquery()
        )
        query = (
            db.query(
                PracticeExam,
                User.display_name.label("owner_name"),
                User.email.label("owner_email"),
                func.coalesce(question_counts.c.question_count, 0).label("actual_question_count"),
            )
            .outerjoin(User, PracticeExam.owner_user_id == User.user_id)
            .outerjoin(question_counts, PracticeExam.exam_id == question_counts.c.exam_id)
        )
        if search:
            query = query.filter(
                or_(
                    PracticeExam.title.ilike(f"%{search}%"),
                    PracticeExam.topic.ilike(f"%{search}%"),
                    PracticeExam.level.ilike(f"%{search}%"),
                    User.display_name.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%"),
                )
            )
        total = _safe_count(query.count())
        rows = query.order_by(PracticeExam.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
        summary = {
            "total_exams": _safe_count(db.query(func.count(PracticeExam.exam_id)).scalar()),
            "total_questions": _safe_count(db.query(func.count(PracticeQuestion.question_id)).scalar()),
            "authored_exams": _safe_count(db.query(func.count(PracticeExam.exam_id)).filter(PracticeExam.owner_user_id.isnot(None)).scalar()),
            "jlpt_levels": _safe_count(db.query(func.count(func.distinct(PracticeExam.level))).scalar()),
        }
        items = []
        for exam, owner_name, owner_email, actual_question_count in rows:
            items.append(
                {
                    "id": str(exam.exam_id),
                    "table": "practice_exams",
                    "data": {
                        "exam_id": str(exam.exam_id),
                        "title": exam.title,
                        "topic": exam.topic,
                        "level": exam.level,
                        "tags": exam.tags or [],
                        "owner_user_id": str(exam.owner_user_id) if exam.owner_user_id else None,
                        "owner_name": owner_name,
                        "owner_email": owner_email,
                        "question_count": _safe_count(actual_question_count) or _safe_count(exam.question_count),
                        "created_at": exam.created_at.isoformat() if exam.created_at else None,
                    },
                }
            )
        return {
            "collection": "exams",
            "summary": summary,
            "items": items,
            "pagination": {**_paginate(page, page_size, total), "query": search},
        }

    raise HTTPException(status_code=404, detail="Collection not found")


@router.get("/me")
async def admin_me(current_user: User = Depends(_require_admin)):
    return {
        "user_id": str(current_user.user_id),
        "email": current_user.email,
        "display_name": current_user.display_name,
    }


@router.get("/dashboard")
async def dashboard(
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    granularity: str | None = Query(default="day"),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(_require_admin),
):
    return _dashboard_payload(
        db,
        current_user,
        start_raw=start_date,
        end_raw=end_date,
        granularity_raw=granularity,
    )


@router.get("/collections/{collection_key}")
async def collection_overview(
    collection_key: str,
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=5, le=50),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(_require_admin),
):
    if collection_key not in COLLECTION_KEYS:
        raise HTTPException(status_code=404, detail="Collection not found")
    return _collection_payload(
        db,
        collection_key=collection_key,
        q=q,
        page=page,
        page_size=page_size,
    )


@router.get("/tables")
async def list_tables(current_user: User = Depends(_require_admin)):
    return [_schema_for_table(table_key) for table_key in TABLES]


@router.get("/tables/{table_key}")
async def list_records(
    table_key: str,
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=5, le=100),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(_require_admin),
):
    if table_key not in TABLES:
        raise HTTPException(status_code=404, detail="Table not found")

    query = _query_for_table(db, table_key, q)
    total = query.count()
    pages = max(math.ceil(total / page_size), 1)
    table = TABLES[table_key]
    records = (
        query.order_by(getattr(table.model, table.primary_key).desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "table": _schema_for_table(table_key),
        "items": [_record_to_dict(table_key, record) for record in records],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": pages,
            "query": q or "",
        },
    }


@router.get("/tables/{table_key}/schema")
async def table_schema(table_key: str, current_user: User = Depends(_require_admin)):
    if table_key not in TABLES:
        raise HTTPException(status_code=404, detail="Table not found")
    return _schema_for_table(table_key)


@router.get("/tables/{table_key}/{record_id}")
async def get_record(
    table_key: str,
    record_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(_require_admin),
):
    if table_key not in TABLES:
        raise HTTPException(status_code=404, detail="Table not found")
    table = TABLES[table_key]
    pk_column = getattr(table.model, table.primary_key).property.columns[0]
    record = db.get(table.model, _coerce_value(pk_column, record_id, is_create=False))
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return {"table": _schema_for_table(table_key), "item": _record_to_dict(table_key, record)}


@router.post("/tables/{table_key}")
async def create_record(
    table_key: str,
    payload: dict[str, Any],
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(_require_admin),
):
    if table_key not in TABLES:
        raise HTTPException(status_code=404, detail="Table not found")
    table = TABLES[table_key]
    values = _validate_payload(table_key, payload, is_create=True)
    if table_key == "users" and payload.get("raw_password"):
        values["password_hash"] = deps.auth_service._hash_password(payload["raw_password"])

    try:
        record = table.model(**values)
        db.add(record)
        db.commit()
        db.refresh(record)
        return {"item": _record_to_dict(table_key, record)}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Create failed: {exc}") from exc


@router.put("/tables/{table_key}/{record_id}")
async def update_record(
    table_key: str,
    record_id: str,
    payload: dict[str, Any],
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(_require_admin),
):
    if table_key not in TABLES:
        raise HTTPException(status_code=404, detail="Table not found")
    table = TABLES[table_key]
    pk_column = getattr(table.model, table.primary_key).property.columns[0]
    record = db.get(table.model, _coerce_value(pk_column, record_id, is_create=False))
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    values = _validate_payload(table_key, payload, is_create=False)

    try:
        for column_name, value in values.items():
            setattr(record, column_name, value)
        if table_key == "users" and payload.get("raw_password"):
            record.password_hash = deps.auth_service._hash_password(payload["raw_password"])
        db.commit()
        db.refresh(record)
        return {"item": _record_to_dict(table_key, record)}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Update failed: {exc}") from exc


@router.delete("/tables/{table_key}/{record_id}")
async def delete_record(
    table_key: str,
    record_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(_require_admin),
):
    if table_key not in TABLES:
        raise HTTPException(status_code=404, detail="Table not found")
    table = TABLES[table_key]
    pk_column = getattr(table.model, table.primary_key).property.columns[0]
    record = db.get(table.model, _coerce_value(pk_column, record_id, is_create=False))
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    if table_key == "users" and str(record.user_id) == str(current_user.user_id):
        raise HTTPException(status_code=400, detail="You cannot delete the current admin session user")
    try:
        db.delete(record)
        db.commit()
        return {"deleted": True, "id": record_id}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Delete failed: {exc}") from exc
