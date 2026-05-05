# Whisper AI Mobile

Android Kotlin frontend cho backend FastAPI trong repo nay.

## Chay backend cho dien thoai truy cap

Tu thu muc goc repo:

```bash
source .venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

## Dia chi backend trong app

- Android Emulator: `http://10.0.2.2:8000`
- Dien thoai that cung Wi-Fi voi may tinh: `http://<IP-LAN-CUA-MAY-TINH>:8000`

Lay IP LAN tren Linux:

```bash
hostname -I
```

Vi du app nhap:

```text
http://192.168.1.20:8000
```

## Mo project

Mo thu muc `android/` bang Android Studio, sync Gradle, roi Run app.

App se:

- Chon file audio/video tren may Android
- Phat file bang Media3
- Upload file len `/api/transcribe`
- Hien transcript theo timestamp
- Highlight cau dang phat
- Hien furigana va tu loai tu response SudachiPy
