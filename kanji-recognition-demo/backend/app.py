from pathlib import Path
import io
import csv
import json
import uuid
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
from PIL import Image, ImageOps, ImageFilter
import torch
import torch.nn as nn
import torchvision.transforms as transforms
from torchvision.models import resnet18

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Kanji Recognition API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"

MODEL_PATH = MODELS_DIR / "best_etl9g_resnet18_synth74_warmup.pth"
LABEL_MAP_PATH = MODELS_DIR / "label_map.csv"

USER_DATA_DIR = BASE_DIR / "user_data"
RAW_STROKES_DIR = USER_DATA_DIR / "raw_strokes"
RAW_CANVAS_DIR = USER_DATA_DIR / "raw_canvas"
PROCESSED_IMAGES_DIR = USER_DATA_DIR / "processed_images"
LABELS_CSV_PATH = USER_DATA_DIR / "labels.csv"
UNLABELED_CSV_PATH = USER_DATA_DIR / "unlabeled.csv"

model = None
label_map = None

preprocess = transforms.Compose([
    transforms.Grayscale(num_output_channels=1),
    transforms.Resize((128, 128)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.5], std=[0.5]),
])


def build_model():
    model = resnet18(weights=None)
    model.conv1 = nn.Conv2d(1, 64, kernel_size=7, stride=2, padding=3, bias=False)
    model.fc = nn.Linear(model.fc.in_features, 3036)
    return model


def ensure_user_data_dirs():
    for directory in [USER_DATA_DIR, RAW_STROKES_DIR, RAW_CANVAS_DIR, PROCESSED_IMAGES_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


def append_csv_row(csv_path: Path, fieldnames: list[str], row: dict):
    file_exists = csv_path.exists()
    with csv_path.open("a", newline='', encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def save_upload_file(upload_file: UploadFile, destination: Path):
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(upload_file.file.read())


def save_json_file(data: dict, destination: Path):
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_model_and_labels():
    global model, label_map

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model file not found: {MODEL_PATH}\n"
            "Please place best_etl9g_resnet18.pth in backend/models/"
        )

    if not LABEL_MAP_PATH.exists():
        raise FileNotFoundError(
            f"Label map file not found: {LABEL_MAP_PATH}\n"
            "Please place label_map.csv in backend/models/"
        )

    label_map_df = pd.read_csv(LABEL_MAP_PATH)
    print("label_map columns:", label_map_df.columns.tolist())

    if "label_id" not in label_map_df.columns:
        raise ValueError("label_map.csv must contain a 'label_id' column")

    if "kanji" in label_map_df.columns:
        char_col = "kanji"
    elif "char" in label_map_df.columns:
        char_col = "char"
    else:
        raise ValueError("label_map.csv must contain either a 'kanji' column or a 'char' column")

    label_map = {
        int(row["label_id"]): str(row[char_col])
        for _, row in label_map_df.iterrows()
    }

    model = build_model()
    state_dict = torch.load(MODEL_PATH, map_location=DEVICE)
    model.load_state_dict(state_dict)
    model.to(DEVICE)
    model.eval()

    print(f"Model loaded successfully on {DEVICE}.")
    print(f"Loaded {len(label_map)} labels.")


@app.on_event("startup")
async def startup_event():
    ensure_user_data_dirs()
    load_model_and_labels()

def preprocess_for_kanji_model(pil_img: Image.Image, out_size: int = 128, pad_ratio: float = 0.12) -> Image.Image:
    img = pil_img.convert("L")
    arr = np.array(img)

    # Nếu nền tối, đảo về nền trắng nét đen
    if arr.mean() < 127:
        arr = 255 - arr

    img = Image.fromarray(arr)
    img = ImageOps.autocontrast(img, cutoff=1)

    arr = np.array(img)

    # Tạo mask nét viết
    mask = arr < 220
    if not mask.any():
        return Image.new("L", (out_size, out_size), 255)

    ys, xs = np.where(mask)
    x1, x2 = xs.min(), xs.max() + 1
    y1, y2 = ys.min(), ys.max() + 1

    crop = arr[y1:y2, x1:x2]
    h, w = crop.shape

    # Pad vuông
    side = int(max(h, w) * (1 + 2 * pad_ratio))
    side = max(side, 8)
    canvas = np.full((side, side), 255, dtype=np.uint8)

    oy = (side - h) // 2
    ox = (side - w) // 2
    canvas[oy:oy+h, ox:ox+w] = crop

    out = Image.fromarray(canvas).resize((out_size, out_size), Image.Resampling.LANCZOS)

    # Threshold lại sau resize
    arr = np.array(out)
    arr = np.where(arr < 220, 0, 255).astype(np.uint8)
    out = Image.fromarray(arr)

    # Làm nét dày nhẹ
    out = out.filter(ImageFilter.MinFilter(3))

    return out
def run_inference(image: Image.Image):
    processed = preprocess_for_kanji_model(image)
    image_array = np.array(processed)
    processed.save("debug_processed.png")

    if np.std(image_array) < 10:
        raise HTTPException(
            status_code=400,
            detail="Canvas appears empty. Please draw a Kanji character."
        )

    input_tensor = preprocess(processed).unsqueeze(0).to(DEVICE)

    with torch.no_grad():
        outputs = model(input_tensor)
        probabilities = torch.softmax(outputs[0], dim=0)
        top5_prob, top5_idx = torch.topk(probabilities, 5)

    top1 = {
        "label_id": int(top5_idx[0].item()),
        "kanji": label_map.get(int(top5_idx[0].item()), "?"),
        "confidence": float(top5_prob[0].item()),
    }

    top5 = [
        {
            "label_id": int(idx.item()),
            "kanji": label_map.get(int(idx.item()), "?"),
            "confidence": float(prob.item()),
        }
        for idx, prob in zip(top5_idx, top5_prob)
    ]

    return {
        "top1": top1,
        "top5": top5,
    }

@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    if model is None:
        raise HTTPException(status_code=500, detail="Model not loaded")

    try:
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data)).convert("L")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image file: {e}")

    return run_inference(image)


@app.post("/predict-drawing")
async def predict_drawing(file: UploadFile = File(...)):
    if model is None:
        raise HTTPException(status_code=500, detail="Model not loaded")

    try:
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data)).convert("L")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image file: {e}")

    return run_inference(image)

## Các endpoint lưu dữ liệu người dùng đã bị xóa để tránh rủi ro bảo mật và quyền riêng tư. Nếu cần, có thể triển khai lại với các biện pháp bảo vệ thích hợp.

# @app.post("/save-drawing")
# async def save_drawing(
#     processed_image: UploadFile = File(...),
#     raw_strokes: str = Form(...),
#     confirmed_label: str = Form(...),
#     confirmed_label_id: Optional[int] = Form(None),
#     top1_pred: str = Form(...),
#     top5_json: str = Form(...),
#     device: str = Form("unknown"),
#     source: str = Form("user_app"),
#     raw_canvas: Optional[UploadFile] = File(None),
# ):
#     sample_id = uuid.uuid4().hex
#     timestamp = datetime.utcnow().isoformat()

#     if not confirmed_label.strip():
#         raise HTTPException(status_code=400, detail="confirmed_label is required")

#     try:
#         raw_strokes_data = json.loads(raw_strokes)
#     except json.JSONDecodeError as e:
#         raise HTTPException(status_code=400, detail=f"Invalid raw_strokes JSON: {e}")

#     top1_data = None
#     top5_data = None
#     try:
#         top1_data = json.loads(top1_pred)
#         top5_data = json.loads(top5_json)
#     except json.JSONDecodeError as e:
#         raise HTTPException(status_code=400, detail=f"Invalid prediction JSON: {e}")

#     raw_strokes_path = RAW_STROKES_DIR / f"{sample_id}.json"
#     processed_image_path = PROCESSED_IMAGES_DIR / f"{sample_id}.png"
#     raw_canvas_path = RAW_CANVAS_DIR / f"{sample_id}.png" if raw_canvas is not None else None

#     save_json_file(raw_strokes_data, raw_strokes_path)
#     save_upload_file(processed_image, processed_image_path)
#     if raw_canvas is not None:
#         save_upload_file(raw_canvas, raw_canvas_path)

#     row = {
#         "sample_id": sample_id,
#         "timestamp": timestamp,
#         "char": confirmed_label,
#         "label_id": confirmed_label_id if confirmed_label_id is not None else 0,
#         "processed_image_path": str(processed_image_path.relative_to(BASE_DIR)),
#         "raw_strokes_path": str(raw_strokes_path.relative_to(BASE_DIR)),
#         "raw_canvas_path": str(raw_canvas_path.relative_to(BASE_DIR)) if raw_canvas_path is not None else "",
#         "source": source,
#         "device": device,
#         "accepted": True,
#         "top1_pred": json.dumps(top1_data, ensure_ascii=False),
#         "top5_json": json.dumps(top5_data, ensure_ascii=False),
#     }

#     append_csv_row(
#         LABELS_CSV_PATH,
#         [
#             "sample_id",
#             "timestamp",
#             "char",
#             "label_id",
#             "processed_image_path",
#             "raw_strokes_path",
#             "raw_canvas_path",
#             "source",
#             "device",
#             "accepted",
#             "top1_pred",
#             "top5_json",
#         ],
#         row,
#     )

#     return {"status": "saved", "sample_id": sample_id}


# @app.post("/save-unlabeled")
# async def save_unlabeled(
#     raw_strokes: str = Form(...),
#     top1_pred: str = Form(...),
#     top5_json: str = Form(...),
#     device: str = Form("unknown"),
#     source: str = Form("user_app"),
#     raw_canvas: Optional[UploadFile] = File(None),
#     processed_image: Optional[UploadFile] = File(None),
# ):
#     sample_id = uuid.uuid4().hex
#     timestamp = datetime.utcnow().isoformat()

#     try:
#         raw_strokes_data = json.loads(raw_strokes)
#     except json.JSONDecodeError as e:
#         raise HTTPException(status_code=400, detail=f"Invalid raw_strokes JSON: {e}")

#     try:
#         top1_data = json.loads(top1_pred)
#         top5_data = json.loads(top5_json)
#     except json.JSONDecodeError as e:
#         raise HTTPException(status_code=400, detail=f"Invalid prediction JSON: {e}")

#     raw_strokes_path = RAW_STROKES_DIR / f"{sample_id}.json"
#     processed_image_path = PROCESSED_IMAGES_DIR / f"{sample_id}.png" if processed_image is not None else None
#     raw_canvas_path = RAW_CANVAS_DIR / f"{sample_id}.png" if raw_canvas is not None else None

#     save_json_file(raw_strokes_data, raw_strokes_path)
#     if processed_image is not None:
#         save_upload_file(processed_image, processed_image_path)
#     if raw_canvas is not None:
#         save_upload_file(raw_canvas, raw_canvas_path)

#     row = {
#         "sample_id": sample_id,
#         "timestamp": timestamp,
#         "processed_image_path": str(processed_image_path.relative_to(BASE_DIR)) if processed_image_path is not None else "",
#         "raw_strokes_path": str(raw_strokes_path.relative_to(BASE_DIR)),
#         "raw_canvas_path": str(raw_canvas_path.relative_to(BASE_DIR)) if raw_canvas_path is not None else "",
#         "source": source,
#         "device": device,
#         "accepted": False,
#         "top1_pred": json.dumps(top1_data, ensure_ascii=False),
#         "top5_json": json.dumps(top5_data, ensure_ascii=False),
#     }

#     append_csv_row(
#         UNLABELED_CSV_PATH,
#         [
#             "sample_id",
#             "timestamp",
#             "processed_image_path",
#             "raw_strokes_path",
#             "raw_canvas_path",
#             "source",
#             "device",
#             "accepted",
#             "top1_pred",
#             "top5_json",
#         ],
#         row,
#     )

#     return {"status": "saved_unlabeled", "sample_id": sample_id}


@app.get("/")
async def root():
    return {
        "message": "Kanji Recognition API is running",
        "device": str(DEVICE),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)