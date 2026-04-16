from pathlib import Path
import io
import json
import math
import uuid
from typing import Optional
from datetime import datetime

import numpy as np
import pandas as pd
from PIL import Image, ImageOps, ImageFilter
import torch
import torch.nn as nn
import torchvision.transforms as transforms
from torchvision.models import resnet18

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx


app = FastAPI(title="Kanji Recognition API", version="2.0.0")

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
USER_DATA_DIR = BASE_DIR / "user_data"

# Create user_data subdirectories if they don't exist
USER_DATA_DIR.mkdir(exist_ok=True)
(USER_DATA_DIR / "raw_strokes").mkdir(exist_ok=True)
(USER_DATA_DIR / "processed_images").mkdir(exist_ok=True)
(USER_DATA_DIR / "raw_canvas").mkdir(exist_ok=True)

MODEL_PATH = MODELS_DIR / "best_etl9g_resnet18_stroke_mixed.pth"
LABEL_MAP_PATH = MODELS_DIR / "label_map.csv"

model = None
label_map = None
model_type = None  # image_only | stroke_aware

preprocess = transforms.Compose([
    transforms.Grayscale(num_output_channels=1),
    transforms.Resize((128, 128)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.5], std=[0.5]),
])


def build_image_only_model():
    model = resnet18(weights=None)
    model.conv1 = nn.Conv2d(1, 64, kernel_size=7, stride=2, padding=3, bias=False)
    model.fc = nn.Linear(model.fc.in_features, 3036)
    return model


class StrokeAwareKanjiModel(nn.Module):
    def __init__(self, num_classes: int = 3036, stroke_dim: int = 24):
        super().__init__()
        self.backbone = resnet18(weights=None)
        self.backbone.conv1 = nn.Conv2d(1, 64, kernel_size=7, stride=2, padding=3, bias=False)
        img_dim = self.backbone.fc.in_features
        self.backbone.fc = nn.Identity()

        self.stroke_mlp = nn.Sequential(
            nn.Linear(stroke_dim, 64),
            nn.ReLU(inplace=True),
            nn.Dropout(0.15),
            nn.Linear(64, 32),
            nn.ReLU(inplace=True),
        )

        self.classifier = nn.Sequential(
            nn.Linear(img_dim + 32, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(0.2),
            nn.Linear(256, num_classes),
        )

    def forward(self, images, stroke_features):
        img_feat = self.backbone(images)
        stroke_feat = self.stroke_mlp(stroke_features)
        feat = torch.cat([img_feat, stroke_feat], dim=1)
        return self.classifier(feat)


def safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return float(default)


async def fetch_kanji_details(kanji: str) -> dict:
    """
    Fetch kanji details from kanjiapi.dev including meanings, readings, and animation.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"https://kanjiapi.dev/v1/kanji/{kanji}")
            if response.status_code == 200:
                data = response.json()
                return {
                    "kanji": kanji,
                    "meanings": data.get("meanings", []),
                    "on_yomi": data.get("on_readings", []),
                    "kun_yomi": data.get("kun_readings", []),
                    "stroke_count": data.get("stroke_count", 0),
                    "jlpt": data.get("jlpt", None),
                    "grade": data.get("grade", None),
                }
            else:
                return {"kanji": kanji, "error": "Kanji not found in API"}
    except Exception as e:
        print(f"Error fetching kanji details: {e}")
        return {"kanji": kanji, "error": str(e)}


def clip01(x):
    return float(max(0.0, min(1.0, x)))


def extract_stroke_features_from_payload(raw_strokes_data: Optional[dict]) -> np.ndarray:
    feat = np.zeros(24, dtype=np.float32)

    if not raw_strokes_data:
        return feat

    strokes = raw_strokes_data.get("strokes", [])
    if not isinstance(strokes, list) or len(strokes) == 0:
        return feat

    canvas_size = raw_strokes_data.get("canvas_size", [128, 128])
    if not isinstance(canvas_size, (list, tuple)) or len(canvas_size) != 2:
        canvas_w, canvas_h = 128.0, 128.0
    else:
        canvas_w = max(safe_float(canvas_size[0], 128.0), 1.0)
        canvas_h = max(safe_float(canvas_size[1], 128.0), 1.0)

    parsed_strokes = []
    for s in strokes:
        if not isinstance(s, list):
            continue
        pts = []
        for pt in s:
            if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                x = safe_float(pt[0]) / canvas_w
                y = safe_float(pt[1]) / canvas_h
                pts.append((clip01(x), clip01(y)))
        if len(pts) >= 1:
            parsed_strokes.append(pts)

    if not parsed_strokes:
        return feat

    all_points = [p for stroke in parsed_strokes for p in stroke]
    xs = np.array([p[0] for p in all_points], dtype=np.float32)
    ys = np.array([p[1] for p in all_points], dtype=np.float32)

    min_x, max_x = float(xs.min()), float(xs.max())
    min_y, max_y = float(ys.min()), float(ys.max())
    width = max_x - min_x
    height = max_y - min_y
    center_x = (min_x + max_x) / 2.0
    center_y = (min_y + max_y) / 2.0
    aspect = width / max(height, 1e-6)

    num_strokes = len(parsed_strokes)
    num_points = len(all_points)

    stroke_lengths = []
    segment_lengths = []
    horizontal = 0
    vertical = 0
    diag_down = 0
    diag_up = 0

    starts = []
    ends = []

    for stroke in parsed_strokes:
        starts.append(stroke[0])
        ends.append(stroke[-1])

        stroke_len = 0.0
        for i in range(1, len(stroke)):
            x1, y1 = stroke[i - 1]
            x2, y2 = stroke[i]
            dx = x2 - x1
            dy = y2 - y1
            seg_len = math.hypot(dx, dy)
            stroke_len += seg_len
            segment_lengths.append(seg_len)

            if seg_len > 1e-8:
                adx = abs(dx)
                ady = abs(dy)
                if adx >= 1.5 * ady:
                    horizontal += 1
                elif ady >= 1.5 * adx:
                    vertical += 1
                else:
                    if dx * dy >= 0:
                        diag_down += 1
                    else:
                        diag_up += 1
        stroke_lengths.append(stroke_len)

    total_length = float(sum(stroke_lengths))
    mean_stroke_len = float(np.mean(stroke_lengths)) if stroke_lengths else 0.0
    std_stroke_len = float(np.std(stroke_lengths)) if stroke_lengths else 0.0
    max_stroke_len = float(np.max(stroke_lengths)) if stroke_lengths else 0.0

    mean_seg_len = float(np.mean(segment_lengths)) if segment_lengths else 0.0
    std_seg_len = float(np.std(segment_lengths)) if segment_lengths else 0.0

    total_dir = max(horizontal + vertical + diag_down + diag_up, 1)
    horizontal_ratio = horizontal / total_dir
    vertical_ratio = vertical / total_dir
    diag_down_ratio = diag_down / total_dir
    diag_up_ratio = diag_up / total_dir

    start_x = float(np.mean([p[0] for p in starts])) if starts else 0.0
    start_y = float(np.mean([p[1] for p in starts])) if starts else 0.0
    end_x = float(np.mean([p[0] for p in ends])) if ends else 0.0
    end_y = float(np.mean([p[1] for p in ends])) if ends else 0.0

    mean_points_per_stroke = num_points / max(num_strokes, 1)
    max_points_in_stroke = max(len(s) for s in parsed_strokes)

    feat[0] = 1.0
    feat[1] = min(num_strokes, 20) / 20.0
    feat[2] = min(num_points, 300) / 300.0
    feat[3] = clip01(width)
    feat[4] = clip01(height)
    feat[5] = math.tanh(aspect - 1.0)
    feat[6] = min(total_length, 4.0) / 4.0
    feat[7] = min(mean_stroke_len, 2.0) / 2.0
    feat[8] = min(std_stroke_len, 2.0) / 2.0
    feat[9] = min(max_stroke_len, 3.0) / 3.0
    feat[10] = min(mean_seg_len, 1.0) / 1.0
    feat[11] = min(std_seg_len, 1.0) / 1.0
    feat[12] = horizontal_ratio
    feat[13] = vertical_ratio
    feat[14] = diag_down_ratio
    feat[15] = diag_up_ratio
    feat[16] = clip01(start_x)
    feat[17] = clip01(start_y)
    feat[18] = clip01(end_x)
    feat[19] = clip01(end_y)
    feat[20] = clip01(center_x)
    feat[21] = clip01(center_y)
    feat[22] = min(mean_points_per_stroke, 60.0) / 60.0
    feat[23] = min(max_points_in_stroke, 100.0) / 100.0

    return feat


def load_model_and_labels():
    global model, label_map, model_type

    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model file not found: {MODEL_PATH}")

    if not LABEL_MAP_PATH.exists():
        raise FileNotFoundError(f"Label map file not found: {LABEL_MAP_PATH}")

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

    state_dict = torch.load(MODEL_PATH, map_location=DEVICE)

    if any(k.startswith("backbone.") for k in state_dict.keys()):
        model = StrokeAwareKanjiModel()
        model.load_state_dict(state_dict, strict=True)
        model_type = "stroke_aware"
    else:
        model = build_image_only_model()
        model.load_state_dict(state_dict, strict=True)
        model_type = "image_only"

    model.to(DEVICE)
    model.eval()

    print(f"Model loaded successfully on {DEVICE}.")
    print(f"Model type: {model_type}")
    print(f"Loaded {len(label_map)} labels.")


@app.on_event("startup")
async def startup_event():
    load_model_and_labels()


def preprocess_for_kanji_model(
    pil_img: Image.Image,
    out_size: int = 128,
    pad_ratio: float = 0.18,
    threshold: int = 160,
    thicken: bool = True,
) -> Image.Image:
    img = pil_img.convert("L")
    arr = np.array(img)

    if arr.mean() < 127:
        arr = 255 - arr

    mask = arr < threshold
    if not mask.any():
        return Image.new("L", (out_size, out_size), 255)

    ys, xs = np.where(mask)
    x1, x2 = xs.min(), xs.max() + 1
    y1, y2 = ys.min(), ys.max() + 1
    crop = arr[y1:y2, x1:x2]

    crop = np.where(crop < threshold, 0, 255).astype(np.uint8)

    h, w = crop.shape
    side = int(max(h, w) * (1 + 2 * pad_ratio))
    side = max(side, 8)

    canvas = np.full((side, side), 255, dtype=np.uint8)
    oy = (side - h) // 2
    ox = (side - w) // 2
    canvas[oy:oy + h, ox:ox + w] = crop

    out = Image.fromarray(canvas).resize((out_size, out_size), Image.Resampling.NEAREST)

    if thicken:
        out = out.filter(ImageFilter.MinFilter(3))

    return out

async def run_inference(image: Image.Image, raw_strokes_data: Optional[dict] = None):
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
        if model_type == "stroke_aware":
            stroke_features = extract_stroke_features_from_payload(raw_strokes_data)
            stroke_tensor = torch.tensor(stroke_features, dtype=torch.float32).unsqueeze(0).to(DEVICE)
            outputs = model(input_tensor, stroke_tensor)
        else:
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

    # Fetch kanji details from API
    top1_kanji = top1.get("kanji", "?")
    if top1_kanji != "?":
        top1["details"] = await fetch_kanji_details(top1_kanji)

    for item in top5:
        kanji = item.get("kanji", "?")
        if kanji != "?":
            item["details"] = await fetch_kanji_details(kanji)

    return {
        "model_type": model_type,
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

    return await run_inference(image)


@app.post("/predict-drawing")
async def predict_drawing(
    file: UploadFile = File(...),
    raw_strokes: Optional[str] = Form(None),
):
    if model is None:
        raise HTTPException(status_code=500, detail="Model not loaded")

    try:
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data)).convert("L")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image file: {e}")

    raw_strokes_data = None
    if raw_strokes:
        try:
            raw_strokes_data = json.loads(raw_strokes)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid raw_strokes JSON: {e}")

    return await run_inference(image, raw_strokes_data=raw_strokes_data)


@app.post("/save-drawing")
async def save_drawing(
    processed_image: UploadFile = File(...),
    raw_strokes: str = Form(...),
    confirmed_label: str = Form(...),
    confirmed_label_id: str = Form(...),
    top1_pred: str = Form(...),
    top5_json: str = Form(...),
    device: str = Form(...),
    source: str = Form(...),
    raw_canvas: Optional[UploadFile] = File(None),
):
    """
    Save a user-confirmed drawing along with metadata.
    """
    try:
        # Generate unique sample ID
        sample_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        # Parse JSON fields
        raw_strokes_data = json.loads(raw_strokes)
        top1_pred_data = json.loads(top1_pred)
        top5_json_data = json.loads(top5_json)

        # Save processed image
        processed_img_data = await processed_image.read()
        processed_img_path = USER_DATA_DIR / "processed_images" / f"{sample_id}.png"
        with open(processed_img_path, "wb") as f:
            f.write(processed_img_data)

        # Save raw canvas if provided
        raw_canvas_path = None
        if raw_canvas:
            raw_canvas_data = await raw_canvas.read()
            raw_canvas_path = USER_DATA_DIR / "raw_canvas" / f"{sample_id}.png"
            with open(raw_canvas_path, "wb") as f:
                f.write(raw_canvas_data)

        # Save raw strokes as JSON
        raw_strokes_path = USER_DATA_DIR / "raw_strokes" / f"{sample_id}.json"
        with open(raw_strokes_path, "w", encoding="utf-8") as f:
            json.dump(raw_strokes_data, f, indent=2, ensure_ascii=False)

        # Create metadata record
        metadata = {
            "sample_id": sample_id,
            "timestamp": timestamp,
            "confirmed_label": confirmed_label,
            "confirmed_label_id": int(confirmed_label_id),
            "predicted_label": top1_pred_data.get("kanji", "?"),
            "predicted_label_id": top1_pred_data.get("label_id", 0),
            "top1_confidence": top1_pred_data.get("confidence", 0.0),
            "top5_predictions": top5_json_data,
            "device": device,
            "source": source,
            "model_type": model_type,
            "processed_image": str(processed_img_path),
            "raw_canvas": str(raw_canvas_path) if raw_canvas_path else None,
            "raw_strokes": str(raw_strokes_path),
        }

        # Update or create labels.csv
        labels_csv_path = USER_DATA_DIR / "labels.csv"
        if labels_csv_path.exists():
            labels_df = pd.read_csv(labels_csv_path)
            new_row = pd.DataFrame([{
                "sample_id": sample_id,
                "timestamp": timestamp,
                "confirmed_label": confirmed_label,
                "confirmed_label_id": int(confirmed_label_id),
                "predicted_label": top1_pred_data.get("kanji", "?"),
                "predicted_label_id": top1_pred_data.get("label_id", 0),
                "top1_confidence": top1_pred_data.get("confidence", 0.0),
                "device": device,
                "source": source,
            }])
            labels_df = pd.concat([labels_df, new_row], ignore_index=True)
        else:
            labels_df = pd.DataFrame([{
                "sample_id": sample_id,
                "timestamp": timestamp,
                "confirmed_label": confirmed_label,
                "confirmed_label_id": int(confirmed_label_id),
                "predicted_label": top1_pred_data.get("kanji", "?"),
                "predicted_label_id": top1_pred_data.get("label_id", 0),
                "top1_confidence": top1_pred_data.get("confidence", 0.0),
                "device": device,
                "source": source,
            }])

        labels_df.to_csv(labels_csv_path, index=False)

        return {
            "status": "success",
            "sample_id": sample_id,
            "message": f"Drawing saved for '{confirmed_label}'",
            "metadata": metadata,
        }

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON in form data: {e}")
    except Exception as e:
        print(f"Error saving drawing: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save drawing: {str(e)}")


@app.get("/")
async def root():
    return {
        "message": "Kanji Recognition API is running",
        "device": str(DEVICE),
        "model_type": model_type,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
