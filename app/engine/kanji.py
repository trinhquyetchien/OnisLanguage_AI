from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torchvision.transforms as transforms
from PIL import Image
from torchvision.models import resnet18

from app.core.config import settings
from app.services.language_service import language_service

logger = logging.getLogger(__name__)


class KanjiModel(nn.Module):
    def __init__(self, num_classes=3036):
        super(KanjiModel, self).__init__()
        self.backbone = resnet18(weights=None)
        self.backbone.conv1 = nn.Conv2d(1, 64, kernel_size=7, stride=2, padding=3, bias=False)
        self.backbone.fc = nn.Identity()
        
        self.stroke_mlp = nn.Sequential(
            nn.Linear(24, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 32)
        )
        
        self.classifier = nn.Sequential(
            nn.Linear(544, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, num_classes)
        )

    def forward(self, x, stroke=None):
        if stroke is None:
            stroke = torch.zeros(x.size(0), 24).to(x.device)
        x_img = self.backbone(x)
        x_stroke = self.stroke_mlp(stroke)
        feat = torch.cat([x_img, x_stroke], dim=1)
        return self.classifier(feat)


class KanjiService:
    def __init__(self) -> None:
        self.model = None
        self.label_map = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.preprocess = transforms.Compose(
            [
                transforms.Grayscale(num_output_channels=1),
                transforms.Resize((128, 128)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.5], std=[0.5]),
            ]
        )

    def _build_model(self):
        return KanjiModel(num_classes=3036)

    def load(self) -> None:
        self._load_resources()

    def _load_resources(self) -> None:
        if self.model is not None:
            return

        logger.info("Loading Kanji Recognition model from %s...", settings.KANJI_MODEL_PATH)

        if not settings.KANJI_MODEL_PATH.exists():
            logger.error("Kanji model not found at %s", settings.KANJI_MODEL_PATH)
            return

        if not settings.KANJI_LABEL_MAP_PATH.exists():
            logger.error("Kanji label map not found at %s", settings.KANJI_LABEL_MAP_PATH)
            return

        df = pd.read_csv(settings.KANJI_LABEL_MAP_PATH)
        char_col = "kanji" if "kanji" in df.columns else "char"
        self.label_map = {int(row["label_id"]): str(row[char_col]) for _, row in df.iterrows()}

        self.model = self._build_model()
        self.model.to(self.device)

        try:
            state_dict = torch.load(settings.KANJI_MODEL_PATH, map_location=self.device)
            self.model.load_state_dict(state_dict)
            self.model.to(self.device)
            self.model.eval()
        except RuntimeError as exc:
            logger.error("Kanji model state_dict is incompatible with current architecture: %s", exc)
            self.model = None
            raise

    def _preprocess_image(self, pil_img: Image.Image) -> Image.Image:
        if pil_img.mode in ("RGBA", "LA") or (pil_img.mode == "P" and "transparency" in pil_img.info):
            bg = Image.new("RGBA", pil_img.size, (255, 255, 255, 255))
            pil_img = Image.alpha_composite(bg, pil_img.convert("RGBA")).convert("L")
        else:
            pil_img = pil_img.convert("L")

        arr = np.array(pil_img)

        if arr.mean() < 127:
            arr = 255 - arr

        binary = np.where(arr < 200, 0, 255).astype(np.uint8)
        ys, xs = np.where(binary == 0)
        if len(ys) == 0:
            return Image.new("L", (128, 128), 255)

        x1, x2 = xs.min(), xs.max() + 1
        y1, y2 = ys.min(), ys.max() + 1
        crop = binary[y1:y2, x1:x2]
        h, w = crop.shape

        side = int(max(h, w) * 1.2)
        canvas = np.full((side, side), 255, dtype=np.uint8)
        oy, ox = (side - h) // 2, (side - w) // 2
        canvas[oy : oy + h, ox : ox + w] = crop

        out = Image.fromarray(canvas).resize((128, 128), Image.Resampling.BILINEAR)
        final_arr = np.where(np.array(out) < 220, 0, 255).astype(np.uint8)
        return Image.fromarray(final_arr)

    def predict(self, image: Image.Image) -> Dict[str, Any]:
        self._load_resources()
        if self.model is None:
            raise RuntimeError("Kanji model failed to load")

        self.model.to(self.device)

        processed = self._preprocess_image(image)
        input_tensor = self.preprocess(processed).unsqueeze(0).to(self.device)

        with torch.no_grad():
            outputs = self.model(input_tensor)
            probs = torch.softmax(outputs[0], dim=0)
            top5_prob, top5_idx = torch.topk(probs, 5)

        results = []
        for prob, idx in zip(top5_prob, top5_idx):
            label_id = int(idx.item())
            results.append(
                {
                    "kanji": self.label_map.get(label_id, "?"),
                    "confidence": float(prob.item()),
                    "label_id": label_id,
                    "meaning_vi": language_service.translate_text(self.label_map.get(label_id, "?"), "ja", "vi"),
                    "analysis": language_service.analyze_text(self.label_map.get(label_id, "?")),
                }
            )

        return {
            "top1": results[0],
            "top5": results,
        }


kanji_engine = KanjiService()
