from __future__ import annotations

import json
import math
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import DateTime, Float, Integer, String, Text, cast, func, or_
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Session
from starlette.datastructures import FormData

from app.core.config import settings
from app.db.models import (
    AudioSample,
    Flashcard,
    FlashcardDeck,
    MediaTranscriptHistory,
    PracticeExam,
    PracticeQuestion,
    User,
)
from app.db.session import SessionLocal
from app.schemas.auth import AuthLoginRequest
from app.services.auth_service import auth_service

templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))
admin_router = APIRouter(prefix="/admin", tags=["Admin"])


@dataclass(frozen=True)
class TableAdmin:
    key: str
    label: str
    model: type
    primary_key: str
    description: str
    accent: str


TABLES: dict[str, TableAdmin] = {
    "users": TableAdmin(
        key="users",
        label="Nguoi dung",
        model=User,
        primary_key="user_id",
        description="Tai khoan, profile va truy cap.",
        accent="#f25f5c",
    ),
    "flashcard_decks": TableAdmin(
        key="flashcard_decks",
        label="Bo the",
        model=FlashcardDeck,
        primary_key="deck_id",
        description="Bo flashcard va metadata hoc tap.",
        accent="#247ba0",
    ),
    "flashcards": TableAdmin(
        key="flashcards",
        label="Flashcard",
        model=Flashcard,
        primary_key="card_id",
        description="Noi dung the hoc chi tiet.",
        accent="#70c1b3",
    ),
    "practice_exams": TableAdmin(
        key="practice_exams",
        label="De thi",
        model=PracticeExam,
        primary_key="exam_id",
        description="De thi luyen tap va thong tin tong quan.",
        accent="#f3a712",
    ),
    "practice_questions": TableAdmin(
        key="practice_questions",
        label="Cau hoi",
        model=PracticeQuestion,
        primary_key="question_id",
        description="Cau hoi chi tiet trong tung de.",
        accent="#9b5de5",
    ),
    "media_transcript_history": TableAdmin(
        key="media_transcript_history",
        label="Lich su media",
        model=MediaTranscriptHistory,
        primary_key="history_id",
        description="Ban ghi OCR, transcribe va media processing.",
        accent="#00bbf9",
    ),
    "audio_samples": TableAdmin(
        key="audio_samples",
        label="Audio mau",
        model=AudioSample,
        primary_key="audio_id",
        description="Kho audio, transcript va tag lien quan.",
        accent="#2a9d8f",
    ),
}


def _build_context(request: Request, **extra: Any) -> dict[str, Any]:
    return {
        "request": request,
        "admin_title": settings.ADMIN_TITLE,
        "tables": list(TABLES.values()),
        "current_path": request.url.path,
        "current_admin_user": request.session.get("admin_user"),
        **extra,
    }


def _db_session() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _is_admin_email(email: str | None) -> bool:
    if not email:
        return False
    normalized = email.strip().lower()
    return "*" in settings.ADMIN_EMAILS or normalized in settings.ADMIN_EMAILS


def _redirect_login() -> RedirectResponse:
    return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)


def _require_admin(request: Request) -> dict[str, Any] | None:
    admin_user = request.session.get("admin_user")
    if not admin_user or not _is_admin_email(admin_user.get("email")):
        return None
    return admin_user


def _serialize_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False, indent=2)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, indent=2)
    return str(value)


def _preview_value(value: Any) -> str:
    text = _serialize_value(value)
    compact = " ".join(text.split())
    if len(compact) > 90:
        return f"{compact[:87]}..."
    return compact


def _column_input_type(column: Any) -> str:
    column_type = column.type
    if isinstance(column_type, (Integer, Float)):
        return "number"
    if isinstance(column_type, DateTime):
        return "datetime-local"
    if isinstance(column_type, UUID):
        return "text"
    return "textarea" if isinstance(column_type, (Text, JSONB, ARRAY)) else "text"


def _coerce_value(column: Any, raw: str | None, *, is_create: bool) -> Any:
    column_type = column.type
    if raw is None:
        return None

    raw = raw.strip()
    if raw == "":
        if column.primary_key and is_create:
            return None
        if not column.nullable and column.default is None and column.server_default is None:
            raise ValueError(f"Truong {column.name} khong duoc de trong.")
        return None

    if isinstance(column_type, Integer):
        return int(raw)
    if isinstance(column_type, Float):
        return float(raw)
    if isinstance(column_type, DateTime):
        return datetime.fromisoformat(raw)
    if isinstance(column_type, UUID):
        return uuid.UUID(raw)
    if isinstance(column_type, JSONB):
        return json.loads(raw)
    if isinstance(column_type, ARRAY):
        if raw.startswith("["):
            return json.loads(raw)
        return [item.strip() for item in raw.replace("\r", "").split("\n") if item.strip()]
    return raw


def _model_columns(table: TableAdmin) -> list[Any]:
    return list(table.model.__table__.columns)


def _editable_columns(table: TableAdmin) -> list[Any]:
    return [column for column in _model_columns(table) if column.name != "created_at"]


def _record_to_form_data(table: TableAdmin, record: Any | None = None) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    for column in _editable_columns(table):
        value = "" if record is None else _serialize_value(getattr(record, column.name))
        fields.append(
            {
                "name": column.name,
                "label": column.name.replace("_", " ").title(),
                "value": value,
                "required": not column.nullable and column.default is None and column.server_default is None and not column.primary_key,
                "readonly": bool(column.primary_key and record is not None),
                "help": str(column.type),
                "input_type": _column_input_type(column),
            }
        )
    if table.key == "users":
        fields.append(
            {
                "name": "raw_password",
                "label": "Raw Password",
                "value": "",
                "required": record is None,
                "readonly": False,
                "help": "Nhap mat khau thuong, he thong se tu hash vao password_hash.",
                "input_type": "text",
            }
        )
    return fields


def _extract_values(table: TableAdmin, form: FormData, *, is_create: bool) -> tuple[dict[str, Any], list[str]]:
    payload: dict[str, Any] = {}
    errors: list[str] = []
    for column in _editable_columns(table):
        try:
            value = _coerce_value(column, form.get(column.name), is_create=is_create)
        except Exception as exc:
            errors.append(str(exc))
            continue

        if value is None and column.primary_key and is_create:
            continue
        if value is None and column.name == "password_hash":
            continue
        payload[column.name] = value

    raw_password = (form.get("raw_password") or "").strip()
    if table.key == "users":
        if raw_password:
            payload["password_hash"] = auth_service._hash_password(raw_password)
        elif is_create and not payload.get("password_hash"):
            errors.append("Truong raw_password hoac password_hash la bat buoc khi tao user.")
    return payload, errors


def _query_for_table(db: Session, table: TableAdmin, q: str | None):
    query = db.query(table.model)
    if q:
        clauses = []
        for column in _model_columns(table):
            if isinstance(column.type, (String, Text, UUID)):
                clauses.append(cast(column, String).ilike(f"%{q}%"))
        if clauses:
            query = query.filter(or_(*clauses))
    return query


@admin_router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if request.session.get("admin_user"):
        return RedirectResponse("/admin", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request,
        "admin/login.html",
        _build_context(request, error=None, email=""),
    )


@admin_router.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    try:
        result = auth_service.login(AuthLoginRequest(email=email, password=password))
    except HTTPException:
        return templates.TemplateResponse(
            request,
            "admin/login.html",
            _build_context(request, error="Sai email hoac mat khau.", email=email),
            status_code=400,
        )

    if not _is_admin_email(result.user.email):
        return templates.TemplateResponse(
            request,
            "admin/login.html",
            _build_context(request, error="Tai khoan nay khong co quyen admin.", email=email),
            status_code=403,
        )

    request.session["admin_user"] = {
        "user_id": result.user.user_id,
        "email": result.user.email,
        "display_name": result.user.display_name,
    }
    return RedirectResponse("/admin", status_code=status.HTTP_303_SEE_OTHER)


@admin_router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)


@admin_router.get("", response_class=HTMLResponse)
@admin_router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(_db_session)):
    if not _require_admin(request):
        return _redirect_login()
    cards = []
    total_records = 0
    for table in TABLES.values():
        count = db.query(func.count()).select_from(table.model).scalar() or 0
        total_records += count
        cards.append({"table": table, "count": count})

    recent_users = db.query(User).order_by(User.created_at.desc()).limit(5).all()
    recent_media = db.query(MediaTranscriptHistory).order_by(MediaTranscriptHistory.created_at.desc()).limit(5).all()

    return templates.TemplateResponse(
        request,
        "admin/dashboard.html",
        _build_context(
            request,
            page_title="Tong quan",
            total_records=total_records,
            cards=cards,
            recent_users=recent_users,
            recent_media=recent_media,
        ),
    )


@admin_router.get("/table/{table_key}", response_class=HTMLResponse)
async def table_list(
    request: Request,
    table_key: str,
    q: str | None = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(_db_session),
):
    if not _require_admin(request):
        return _redirect_login()
    table = TABLES.get(table_key)
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    page = max(page, 1)
    page_size = min(max(page_size, 5), 100)
    query = _query_for_table(db, table, q)
    total = query.count()
    pages = max(math.ceil(total / page_size), 1)
    records = (
        query.order_by(getattr(table.model, table.primary_key).desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    columns = [column.name for column in _model_columns(table)]

    return templates.TemplateResponse(
        request,
        "admin/table_list.html",
        _build_context(
            request,
            page_title=table.label,
            table=table,
            columns=columns,
            records=records,
            preview_value=_preview_value,
            total=total,
            page=page,
            pages=pages,
            page_size=page_size,
            q=q or "",
        ),
    )


@admin_router.get("/table/{table_key}/new", response_class=HTMLResponse)
async def new_record_page(request: Request, table_key: str):
    if not _require_admin(request):
        return _redirect_login()
    table = TABLES.get(table_key)
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    return templates.TemplateResponse(
        request,
        "admin/record_form.html",
        _build_context(
            request,
            page_title=f"Tao moi {table.label}",
            table=table,
            mode="create",
            record_id=None,
            fields=_record_to_form_data(table),
            error=None,
        ),
    )


@admin_router.post("/table/{table_key}/new", response_class=HTMLResponse)
async def create_record(request: Request, table_key: str, db: Session = Depends(_db_session)):
    if not _require_admin(request):
        return _redirect_login()
    table = TABLES.get(table_key)
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    form = await request.form()
    payload, errors = _extract_values(table, form, is_create=True)
    if errors:
        return templates.TemplateResponse(
            request,
            "admin/record_form.html",
            _build_context(
                request,
                page_title=f"Tao moi {table.label}",
                table=table,
                mode="create",
                record_id=None,
                fields=_record_to_form_data(table),
                error="; ".join(errors),
            ),
            status_code=400,
        )

    try:
        record = table.model(**payload)
        db.add(record)
        db.commit()
    except Exception as exc:
        db.rollback()
        return templates.TemplateResponse(
            request,
            "admin/record_form.html",
            _build_context(
                request,
                page_title=f"Tao moi {table.label}",
                table=table,
                mode="create",
                record_id=None,
                fields=_record_to_form_data(table),
                error=f"Loi luu du lieu: {exc}",
            ),
            status_code=400,
        )

    return RedirectResponse(f"/admin/table/{table_key}", status_code=status.HTTP_303_SEE_OTHER)


@admin_router.get("/table/{table_key}/{record_id}", response_class=HTMLResponse)
async def edit_record_page(request: Request, table_key: str, record_id: str, db: Session = Depends(_db_session)):
    if not _require_admin(request):
        return _redirect_login()
    table = TABLES.get(table_key)
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    record = db.get(table.model, _coerce_value(getattr(table.model, table.primary_key).property.columns[0], record_id, is_create=False))
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    return templates.TemplateResponse(
        request,
        "admin/record_form.html",
        _build_context(
            request,
            page_title=f"Chinh sua {table.label}",
            table=table,
            mode="edit",
            record_id=record_id,
            fields=_record_to_form_data(table, record),
            error=None,
        ),
    )


@admin_router.post("/table/{table_key}/{record_id}", response_class=HTMLResponse)
async def update_record(request: Request, table_key: str, record_id: str, db: Session = Depends(_db_session)):
    if not _require_admin(request):
        return _redirect_login()
    table = TABLES.get(table_key)
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    pk_column = getattr(table.model, table.primary_key).property.columns[0]
    record = db.get(table.model, _coerce_value(pk_column, record_id, is_create=False))
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    form = await request.form()
    payload, errors = _extract_values(table, form, is_create=False)
    if errors:
        return templates.TemplateResponse(
            request,
            "admin/record_form.html",
            _build_context(
                request,
                page_title=f"Chinh sua {table.label}",
                table=table,
                mode="edit",
                record_id=record_id,
                fields=_record_to_form_data(table, record),
                error="; ".join(errors),
            ),
            status_code=400,
        )

    try:
        for key, value in payload.items():
            if key == table.primary_key:
                continue
            setattr(record, key, value)
        db.commit()
    except Exception as exc:
        db.rollback()
        return templates.TemplateResponse(
            request,
            "admin/record_form.html",
            _build_context(
                request,
                page_title=f"Chinh sua {table.label}",
                table=table,
                mode="edit",
                record_id=record_id,
                fields=_record_to_form_data(table, record),
                error=f"Loi cap nhat du lieu: {exc}",
            ),
            status_code=400,
        )

    return RedirectResponse(f"/admin/table/{table_key}/{record_id}", status_code=status.HTTP_303_SEE_OTHER)


@admin_router.post("/table/{table_key}/{record_id}/delete")
async def delete_record(request: Request, table_key: str, record_id: str, db: Session = Depends(_db_session)):
    if not _require_admin(request):
        return _redirect_login()
    table = TABLES.get(table_key)
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    pk_column = getattr(table.model, table.primary_key).property.columns[0]
    record = db.get(table.model, _coerce_value(pk_column, record_id, is_create=False))
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    try:
        db.delete(record)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Khong the xoa ban ghi: {exc}") from exc

    return RedirectResponse(f"/admin/table/{table_key}", status_code=status.HTTP_303_SEE_OTHER)
