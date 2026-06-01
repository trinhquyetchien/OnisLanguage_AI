from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from paddleocr import PaddleOCR


JAPANESE_CHAR_RE = re.compile(
    r"[0-9０-９\u3040-\u30ff\u31f0-\u31ff\u3400-\u4dbf\u4e00-\u9fff\uff66-\uff9f\u3000-\u303f々ー]+"
)


def extract_japanese_text(text: str) -> str:
    if not text:
        return ""
    parts = JAPANESE_CHAR_RE.findall(text)
    cleaned = " ".join(part.strip() for part in parts if part.strip())
    return re.sub(r"\s+", " ", cleaned).strip()


def main() -> int:
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: paddle_ocr_worker.py <image_path> <model_dir>"}))
        return 1

    image_path = Path(sys.argv[1]).resolve()
    model_dir = Path(sys.argv[2]).resolve()
    os.environ.setdefault("PADDLE_HOME", str(model_dir))

    ocr = PaddleOCR(
        lang="japan",
        ocr_version="PP-OCRv3",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )
    results = ocr.predict(str(image_path))
    result = results[0] if results else None

    rec_texts = list(result["rec_texts"]) if result else []
    rec_scores = list(result["rec_scores"]) if result else []
    rec_polys = list(result["rec_polys"]) if result else []

    blocks = []
    full_text_lines: list[str] = []
    for text, score, poly in zip(rec_texts, rec_scores, rec_polys):
        normalized_text = extract_japanese_text(str(text).strip())
        if not normalized_text:
            continue
        box = [[float(point[0]), float(point[1])] for point in poly]
        blocks.append(
            {
                "text": normalized_text,
                "confidence": float(score or 0.0),
                "box": box,
            }
        )
        full_text_lines.append(normalized_text)

    payload = {
        "full_text": "\n".join(full_text_lines),
        "blocks": blocks,
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
