# OnisLanguage Backend

Backend API cho app học tiếng Nhật. Repo này chỉ còn phần backend, được tổ chức theo FastAPI với Swagger/OpenAPI sẵn có tại `/docs`.

## Chức năng chính
- `image-to-text` cho OCR tiếng Nhật.
- `speech-to-text` cho file audio.
- `media-to-text` cho file audio hoặc video.
- `draw-and-recognize` cho nhận dạng kanji từ ảnh vẽ.
- `practice exams` để tạo và chấm đề thi thử.
- `flashcards` để quản lý thư viện flashcard.

## Cấu trúc
- `backend/app/main.py`: FastAPI entrypoint.
- `backend/app/api/v1/endpoints/`: routes theo nhóm chức năng.
- `backend/app/services/`: logic xử lý AI và nghiệp vụ.
- `backend/app/schemas/`: schema request/response.
- `backend/models/`: model weights và label map.
- `backend/storage/`: file upload tạm.

## Chạy local
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Swagger
- OpenAPI JSON: `/openapi.json`
- Swagger UI: `/docs`
- ReDoc: `/redoc`

## PostgreSQL schema
Schema tạo database nằm tại `backend/db/schema.sql`.

Ví dụ chạy local:
```bash
createdb onis_language
psql -d onis_language -f backend/db/schema.sql
```

Các bảng chính:
- `users`, `auth_sessions`: đăng ký, đăng nhập, token.
- `flashcard_decks`, `flashcards`, `flashcard_reviews`: bộ thẻ, thẻ học, lịch ôn.
- `practice_exams`, `practice_questions`, `practice_submissions`: đề thi, câu hỏi, bài nộp.
- `sync_events`, `sync_cursors`: đồng bộ client/backend theo cursor.

API sync trên Swagger:
- `POST /api/v1/sync/push`: client đẩy thay đổi local lên server.
- `GET /api/v1/sync/pull?user_id=...&since=...`: client kéo thay đổi mới từ server.
- `GET /api/v1/sync/snapshot?user_id=...`: lấy snapshot dữ liệu để bootstrap thiết bị mới.
