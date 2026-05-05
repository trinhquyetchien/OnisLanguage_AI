# Whisper AI Local Transcriber

Ung dung chay local de tai file am thanh/video len, goi backend FastAPI, dung model Whisper chuyen thanh van ban va hien thi tren web.

## Yeu cau

- Python 3.10+
- FFmpeg da cai tren may

Kiem tra FFmpeg:

```bash
ffmpeg -version
```

Neu chua co FFmpeg tren Ubuntu/Debian:

```bash
sudo apt update
sudo apt install ffmpeg
```

## Cai dat

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Chay ung dung

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Mo trinh duyet:

```text
http://127.0.0.1:8000
```

Neu dung Android app trong thu muc `android/`, chay backend cho thiet bi khac trong LAN truy cap:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Lan dau chay, Whisper se tai model ve may. Mac dinh dung model `base` va ngon ngu `ja` de nhan dang tieng Nhat.

Co the doi model bang bien moi truong:

```bash
WHISPER_MODEL=small uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Mot so model hop le: `tiny`, `base`, `small`, `medium`, `large`.

Co the doi ngon ngu Whisper bang bien moi truong:

```bash
WHISPER_LANGUAGE=vi uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

## API

```http
POST /api/transcribe
Content-Type: multipart/form-data
file=<audio_or_video_file>
```

Response:

```json
{
  "text": "noi dung da nhan dang",
  "language": "ja",
  "segments": [
    {
      "id": 0,
      "start": 0.0,
      "end": 3.5,
      "text": "..."
    }
  ],
  "duration_seconds": 12.34
}
```

## Phan tich tieng Nhat

Backend dung `SudachiPy` va `SudachiDict-core` de tach tu, lay tu loai, dang goc va cach doc furigana cho Kanji.

Test rieng khong can upload audio:

```bash
curl -X POST http://127.0.0.1:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"text":"私は日本語を勉強します。"}'
```
