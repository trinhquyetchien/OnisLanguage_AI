import logging
import torch
import torch.nn as nn
from torchvision.models import resnet18
import torchvision.transforms as transforms
from PIL import Image, ImageOps, ImageFilter
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List
from app.core.config import settings

logger = logging.getLogger(__name__)

class KanjiService:
    def __init__(self):
        self.model = None
        self.label_map = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.preprocess = transforms.Compose([
            transforms.Grayscale(num_output_channels=1),
            transforms.Resize((128, 128)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.5], std=[0.5]),
        ])

    def _build_model(self):
        model = resnet18(weights=None)
        model.conv1 = nn.Conv2d(1, 64, kernel_size=7, stride=2, padding=3, bias=False)
        model.fc = nn.Linear(model.fc.in_features, 3036)
        return model

    def load(self):
        """Public method to pre-load resources"""
        self._load_resources()

    def _load_resources(self):
        if self.model is not None:
            return

        logger.info(f"Loading Kanji Recognition model from {settings.KANJI_MODEL_PATH}...")
        
        if not settings.KANJI_MODEL_PATH.exists():
            logger.error(f"Kanji model not found at {settings.KANJI_MODEL_PATH}")
            return

        if not settings.KANJI_LABEL_MAP_PATH.exists():
            logger.error(f"Kanji label map not found at {settings.KANJI_LABEL_MAP_PATH}")
            return

        # Load labels
        df = pd.read_csv(settings.KANJI_LABEL_MAP_PATH)
        char_col = "kanji" if "kanji" in df.columns else "char"
        self.label_map = {int(row["label_id"]): str(row[char_col]) for _, row in df.iterrows()}

        # Load model
        self.model = self._build_model()
        self.model.to(self.device)  # Move model to device before loading state dict
        
        state_dict = torch.load(settings.KANJI_MODEL_PATH, map_location=self.device)
        self.model.load_state_dict(state_dict)
        self.model.to(self.device)  # Ensure everything is on device
        self.model.eval()

    def _preprocess_image(self, pil_img: Image.Image) -> Image.Image:
        # Handle transparency: composite onto white background
        if pil_img.mode in ("RGBA", "LA") or (pil_img.mode == "P" and "transparency" in pil_img.info):
            bg = Image.new("RGBA", pil_img.size, (255, 255, 255, 255))
            pil_img = Image.alpha_composite(bg, pil_img.convert("RGBA")).convert("L")
        else:
            pil_img = pil_img.convert("L")

        arr = np.array(pil_img)
        
        # Ensure strokes are dark (0) and background is light (255)
        # In a typical drawing canvas, strokes are dark. 
        # If the image is mostly dark, invert it.
        if arr.mean() < 127:
            arr = 255 - arr
        
        # Threshold to get clean binary image (0 for stroke, 255 for bg)
        # Use a simple global threshold
        binary = np.where(arr < 200, 0, 255).astype(np.uint8)
        
        # Find bounding box of the stroke (0)
        ys, xs = np.where(binary == 0)
        if len(ys) == 0:
            return Image.new("L", (128, 128), 255)
            
        x1, x2 = xs.min(), xs.max() + 1
        y1, y2 = ys.min(), ys.max() + 1
        
        # Crop the stroke
        crop = binary[y1:y2, x1:x2]
        h, w = crop.shape
        
        # Add padding and make square
        side = int(max(h, w) * 1.2)
        canvas = np.full((side, side), 255, dtype=np.uint8)
        oy, ox = (side - h) // 2, (side - w) // 2
        canvas[oy:oy+h, ox:ox+w] = crop
        
        # Resize to 128x128
        out = Image.fromarray(canvas).resize((128, 128), Image.Resampling.BILINEAR)
        
        # Final cleanup: sharpen and ensure binary
        final_arr = np.where(np.array(out) < 220, 0, 255).astype(np.uint8)
        return Image.fromarray(final_arr)

    def predict(self, image: Image.Image) -> Dict[str, Any]:
        self._load_resources()
        if self.model is None:
            raise RuntimeError("Kanji model failed to load")

        # Defensive: ensure model is on the correct device
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
            results.append({
                "kanji": self.label_map.get(label_id, "?"),
                "confidence": float(prob.item()),
                "label_id": label_id
            })

        return {
            "top1": results[0],
            "top5": results
        }

kanji_service = KanjiService()
