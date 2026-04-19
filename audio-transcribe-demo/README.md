# Audio Transcribe Demo

Web app học tiếng Nhật qua audio/video với transcript theo segment và đồng bộ timestamp theo thời gian phát.

## Features

- Upload file audio hoặc video
- Backend FastAPI dùng local Whisper model để transcribe
- Hỗ trợ segment transcript với `start`, `end`, `text_ja`
- Frontend React phát media, highlight segment đang phát, click segment để seek
- Auto-scroll transcript theo playback
- Giao diện card-based, dark/light friendly

## Tech Stack

- Frontend: React + TypeScript + Vite + Tailwind CSS
- Backend: FastAPI
- Model: local Whisper model tại `model-transcribe-v1`

## Project Structure

```text
audio-transcribe-demo/
  backend/
    app/
      config.py
      main.py
      schemas.py
      services/
        infer.py
        media.py
    storage/
      uploads/
  frontend/
    src/
      components/
      lib/
```

## Requirements

- Windows PowerShell
- Python 3.10+ hoặc tương đương
- Node.js 18+ và npm
- `ffmpeg` trong `PATH` nếu muốn transcribe `mp4`, `mov`, `mkv`, `webm`
- Local model `model-transcribe-v1`

## Model Location

Backend tự dò model theo thứ tự:

1. `audio-transcribe-demo/backend/app/model-transcribe-v1`
2. `model-transcribe-v1` ở root repo

Khuyến nghị chỉ giữ một bản model để tránh nhầm path.

## Backend Setup

Từ root repo:

```powershell
cd audio-transcribe-demo\backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Nếu bạn đã có `.venv` ở root repo và muốn dùng luôn:

```powershell
cd audio-transcribe-demo\backend
..\..\.venv\Scripts\activate
```

Nếu lệnh trên không tiện, cứ dùng Python interpreter bạn đang chạy được với `fastapi`, `torch`, `transformers`, `librosa`.

## Run Backend

```powershell
cd audio-transcribe-demo\backend
uvicorn app.main:app --reload
```

Backend mặc định chạy tại:

```text
http://127.0.0.1:8000
```

### Backend API

- `GET /health`
- `POST /api/transcribe`
- `GET /media/<stored_filename>`

## Frontend Setup

```powershell
cd audio-transcribe-demo\frontend
npm install
```

## Run Frontend

```powershell
cd audio-transcribe-demo\frontend
npm run dev
```

Frontend mặc định chạy tại:

```text
http://127.0.0.1:5173
```

Frontend hiện đang gọi backend cứng ở `http://127.0.0.1:8000`.

## How To Use

1. Start backend.
2. Start frontend.
3. Mở `http://127.0.0.1:5173`.
4. Upload một file `mp3`, `wav`, `m4a`, `mp4`, `flac`, `ogg`, `aac`, `webm`, `mov`, hoặc `mkv`.
5. Chờ backend transcribe.
6. Phát media, click transcript segment để nhảy timestamp, bật hoặc tắt auto-scroll nếu cần.

## Transcript Response Format

Backend trả JSON dạng:

```json
{
  "audio_filename": "example.mp3",
  "duration": 123.45,
  "full_text_ja": "おはようございます",
  "segments": [
    {
      "segment_id": 0,
      "start": 0.0,
      "end": 3.52,
      "text_ja": "おはようございます"
    }
  ],
  "media_url": "/media/xxxx_example.mp3",
  "media_kind": "audio"
}
```

## Supported Formats

- Audio: `mp3`, `wav`, `m4a`, `flac`, `ogg`, `aac`
- Video: `mp4`, `webm`, `mov`, `mkv`

## Notes

- File upload được lưu trong `audio-transcribe-demo/backend/storage/uploads/`
- Nếu Whisper timestamp path lỗi, backend tự fallback sang manual chunking
- Audio dài sẽ được chia chunk trước khi transcribe
- Chất lượng transcript phụ thuộc trực tiếp vào model local

## Troubleshooting

### 1. `500 Internal Server Error` khi upload

Kiểm tra:

- model có tồn tại đúng path không
- backend có quyền đọc model không
- file upload có đúng format hỗ trợ không

Test nhanh:

```powershell
cd audio-transcribe-demo\backend
uvicorn app.main:app --reload
```

Mở:

```text
http://127.0.0.1:8000/health
```

### 2. Video không transcribe được

Nguyên nhân phổ biến là thiếu `ffmpeg`.

Kiểm tra:

```powershell
ffmpeg -version
```

### 3. Frontend không gọi được backend

Đảm bảo:

- backend đang chạy ở `127.0.0.1:8000`
- frontend đang chạy ở `127.0.0.1:5173`
- không có process khác chiếm port

### 4. Transcript chậm hoặc nặng máy

Nguyên nhân:

- file quá dài
- model local nặng
- đang chạy trên CPU

## Recommended Cleanup

Nếu muốn cấu trúc sạch hơn, nên giữ:

- `audio-transcribe-demo/`
- một bản duy nhất của `model-transcribe-v1`

và bỏ các thư mục cũ không còn dùng đến sau khi xác nhận app chạy ổn.
