from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path


BASE_URL = "http://127.0.0.1:8000/api/v1"
BACKEND_DIR = Path(__file__).resolve().parents[1]
UPLOADS_DIR = BACKEND_DIR / "data" / "uploads"

LOGIN_EMAIL = "demo@onis.app"
LOGIN_PASSWORD = "123456"

OCR_IMAGE = UPLOADS_DIR / "3184cc462f12431da77fb97bb5b9a951_ocr_camera_1778771021721.jpg"
KANJI_IMAGE = UPLOADS_DIR / "06081e0e9a9942e59a503eb9048e8f6c_ocr_1778697584701_thumb_1200_1553.png"
SHORT_AUDIO = UPLOADS_DIR / "31316a5d8d4b4dbaa85ea9ff3e11a305_transcribe_test_15s.mp3"
LONG_MEDIA = UPLOADS_DIR / "fc7046df3d5944148221f133b4ca29ea_1c0703a51913a0a3e59d8e4374804c5f_1778702520735.mp4"


def run_curl(args: list[str], *, timeout: int = 1800) -> tuple[int, str, str, float]:
    start = time.perf_counter()
    completed = subprocess.run(
        ["curl", "-sS", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    elapsed = time.perf_counter() - start
    return completed.returncode, completed.stdout, completed.stderr, elapsed


def request_json(method: str, path: str, *, token: str | None = None, body: dict | None = None) -> dict:
    args = ["-X", method, f"{BASE_URL}{path}", "-H", "Content-Type: application/json"]
    if token:
        args.extend(["-H", f"Authorization: Bearer {token}"])
    if body is not None:
        args.extend(["-d", json.dumps(body, ensure_ascii=False)])
    code, stdout, stderr, elapsed = run_curl(args)
    payload = json.loads(stdout) if stdout else {}
    return {
        "path": path,
        "returncode": code,
        "elapsed_seconds": round(elapsed, 3),
        "stderr": stderr.strip(),
        "payload": payload,
    }


def request_file(path: str, file_path: Path, *, token: str | None = None, field_name: str = "file") -> dict:
    args = ["-X", "POST", f"{BASE_URL}{path}", "-F", f"{field_name}=@{file_path}"]
    if token:
        args.extend(["-H", f"Authorization: Bearer {token}"])
    code, stdout, stderr, elapsed = run_curl(args)
    payload = json.loads(stdout) if stdout else {}
    return {
        "path": path,
        "file": file_path.name,
        "returncode": code,
        "elapsed_seconds": round(elapsed, 3),
        "stderr": stderr.strip(),
        "payload": payload,
    }


def summarize(result: dict) -> str:
    payload = result.get("payload") or {}
    if "detail" in payload:
        summary = f"detail={payload['detail']}"
    elif "response" in payload:
        summary = f"response_chars={len(payload.get('response') or '')}"
    elif "questions" in payload:
        summary = f"questions={len(payload.get('questions') or [])}"
    elif "full_text_ja" in payload:
        summary = (
            f"text_chars={len(payload.get('full_text_ja') or '')}, "
            f"segments={len(payload.get('segments') or [])}, "
            f"duration={payload.get('duration')}"
        )
    elif "translated_text" in payload:
        summary = f"translated_chars={len(payload.get('translated_text') or '')}"
    elif "analysis" in payload and "normalized_text" in payload:
        analysis = payload.get("analysis") or {}
        summary = (
            f"normalized_chars={len(payload.get('normalized_text') or '')}, "
            f"vocab={len(analysis.get('vocabulary') or [])}, "
            f"grammar={len(analysis.get('grammar_points') or [])}"
        )
    elif "image_url" in payload:
        summary = (
            f"text_chars={len(payload.get('full_text') or '')}, "
            f"sentences={len(payload.get('sentences') or [])}"
        )
    elif "top1" in payload:
        top1 = payload.get("top1") or {}
        summary = f"top1={top1.get('kanji')}, confidence={top1.get('confidence')}"
    else:
        summary = f"keys={sorted(payload.keys())}"
    return (
        f"{result['path']}: {result['elapsed_seconds']}s "
        f"(curl_rc={result['returncode']}) {summary}"
    )


def main() -> int:
    login = request_json(
        "POST",
        "/auth/login",
        body={"email": LOGIN_EMAIL, "password": LOGIN_PASSWORD},
    )
    print(summarize(login))
    token = (login.get("payload") or {}).get("access_token")
    if not token:
        print(json.dumps(login, ensure_ascii=False, indent=2))
        return 1

    long_japanese = "日本語の学習では、毎日少しずつでも継続することが大切です。" * 24
    requests_to_run = [
        ("json", {"method": "POST", "path": "/language/translate", "token": token, "body": {
            "text": long_japanese,
            "source_language": "ja",
            "target_language": "vi",
        }}),
        ("json", {"method": "POST", "path": "/language/analyze", "token": token, "body": {
            "text": "昨日は図書館で日本語の文法を勉強してから、友達と一緒に晩ご飯を食べました。",
            "language": "ja",
        }}),
        ("file", {"path": "/ai/ocr/image-to-text", "token": token, "file_path": OCR_IMAGE}),
        ("file", {"path": "/ai/kanji/draw-and-recognize", "token": token, "file_path": KANJI_IMAGE}),
        ("file", {"path": "/ai/transcribe/speech-to-text", "token": token, "file_path": SHORT_AUDIO}),
        ("file", {"path": "/ai/transcribe/media-to-text", "token": token, "file_path": LONG_MEDIA}),
        ("json", {"method": "POST", "path": "/ai/chat/", "token": token, "body": {
            "messages": [{"role": "user", "content": "Giải thích ngắn gọn sự khác nhau giữa は và が bằng tiếng Việt."}],
        }}),
        ("json", {"method": "POST", "path": "/practice/generate-ai", "token": token, "body": {
            "topic": "Trợ từ cơ bản N5",
            "count": 3,
        }}),
    ]

    results: list[dict] = [login]
    for mode, kwargs in requests_to_run:
        if mode == "json":
            result = request_json(**kwargs)
        else:
            result = request_file(**kwargs)
        results.append(result)
        print(summarize(result))

    failures = [
        result for result in results
        if result["returncode"] != 0 or "detail" in (result.get("payload") or {})
    ]
    if failures:
        print("\nFailures:")
        for failure in failures:
            print(json.dumps(failure, ensure_ascii=False, indent=2)[:4000])
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
