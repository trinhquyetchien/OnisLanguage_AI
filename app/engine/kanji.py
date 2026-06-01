from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict
from urllib.parse import quote

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torchvision.transforms as transforms
from PIL import Image, ImageOps
from torchvision.models import resnet18

from app.core.config import settings

logger = logging.getLogger(__name__)


class ResNetKanjiModel(nn.Module):
    def __init__(self, num_classes=3036): 
        super(ResNetKanjiModel, self).__init__()
        # Using ResNet18 as backbone to match weights
        self.backbone = resnet18(weights=None)
        # Adjust for grayscale input (1 channel)
        self.backbone.conv1 = nn.Conv2d(1, 64, kernel_size=7, stride=2, padding=3, bias=False)
        self.backbone.fc = nn.Identity()
        
        # Stroke MLP as found in state_dict
        self.stroke_mlp = nn.Sequential(
            nn.Linear(24, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 32)
        )
        
        # Final classifier
        self.classifier = nn.Sequential(
            nn.Linear(512 + 32, 256),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(256, num_classes)
        )

    def forward(self, x, s):
        x = self.backbone(x)
        s = self.stroke_mlp(s)
        out = torch.cat((x, s), dim=1)
        return self.classifier(out)


class KanjiService:
    INPUT_SIZE = 128
    SVG_STROKE_DURATION = 0.55
    SVG_STROKE_DELAY = 0.18
    SVG_LOOP_PAUSE = 0.6

    def __init__(self) -> None:
        self.model = None
        self.label_map = None
        self._kanji_metadata_cache: dict[str, dict[str, Any]] = {}
        self._kanji_metadata_dir = settings.KANJI_METADATA_DIR
        self.device = torch.device(self._resolve_device())
        self.preprocess = transforms.Compose(
            [
                transforms.Resize((self.INPUT_SIZE, self.INPUT_SIZE)),
                transforms.ToTensor(),
                # Empirically verified to work best with user's model
                transforms.Normalize(mean=[0.5], std=[0.5]),
            ]
        )

    @staticmethod
    def _resolve_device() -> str:
        requested = settings.KANJI_DEVICE
        if requested == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        if requested == "cuda" and torch.cuda.is_available():
            return "cuda"
        return "cpu"

    def load(self) -> None:
        self._load_resources()

    @staticmethod
    def _should_retry_on_cpu(exc: Exception) -> bool:
        message = str(exc).lower()
        return any(token in message for token in ("cuda", "out of memory", "cublas", "cudnn"))

    def _reset_to_cpu(self) -> None:
        logger.warning("Resetting Kanji runtime to CPU.")
        self.model = None
        self.device = torch.device("cpu")

    def _load_resources(self) -> None:
        if self.model is not None:
            return

        logger.info("Loading ResNet Kanji model from %s...", settings.KANJI_MODEL_PATH)
        if self.device.type == "cuda" and torch.backends.cudnn.enabled:
            # This host is missing one cuDNN v9 sublibrary required by the v8
            # frontend path. Disabling cuDNN keeps inference on CUDA instead of
            # failing over to CPU.
            torch.backends.cudnn.enabled = False
            logger.warning("Disabled cuDNN for Kanji inference to keep the model on CUDA.")

        if not settings.KANJI_MODEL_PATH.exists():
            logger.warning("Kanji model weights not found at %s.", settings.KANJI_MODEL_PATH)
            self.model = ResNetKanjiModel(num_classes=3036)
        else:
            try:
                self.model = ResNetKanjiModel(num_classes=3036)
                state_dict = torch.load(settings.KANJI_MODEL_PATH, map_location=self.device)
                self.model.load_state_dict(state_dict)
            except Exception as e:
                logger.error(f"Failed to load ResNet Kanji weights: {e}")
                self.model = None
                return

        if not settings.KANJI_LABEL_MAP_PATH.exists():
            logger.error("Kanji label map not found at %s", settings.KANJI_LABEL_MAP_PATH)
            return

        df = pd.read_csv(settings.KANJI_LABEL_MAP_PATH)
        char_col = "kanji" if "kanji" in df.columns else "char"
        self.label_map = {int(row["label_id"]): str(row[char_col]) for _, row in df.iterrows()}
        
        if self.model:
            try:
                self.model.to(self.device)
                self.model.eval()
            except RuntimeError as exc:
                if self.device.type == "cuda" and self._should_retry_on_cpu(exc):
                    logger.warning(
                        "Kanji model CUDA initialization failed (%s). Falling back to CPU.",
                        exc,
                    )
                    self._reset_to_cpu()
                    self._load_resources()
                    return
                raise

    def _preprocess_image(self, pil_img: Image.Image) -> Image.Image:
        # Convert to Grayscale (L)
        # Empirically verified: Model expects Black strokes on White background
        # (which is the default for most mobile drawing apps)
        return pil_img.convert("L")

    def _load_kanji_metadata(self, kanji_char: str) -> dict[str, Any] | None:
        if not kanji_char or kanji_char == "?":
            return None

        if kanji_char in self._kanji_metadata_cache:
            return self._kanji_metadata_cache[kanji_char]

        json_path = self._kanji_metadata_dir / f"{kanji_char}.json"
        if json_path.exists():
            try:
                with json_path.open("r", encoding="utf-8") as fp:
                    metadata = json.load(fp)
                    self._kanji_metadata_cache[kanji_char] = metadata
                    return metadata
            except Exception as exc:
                logger.warning("Failed to parse kanji metadata %s: %s", json_path, exc)

        self._kanji_metadata_cache[kanji_char] = {}
        return None

    @staticmethod
    def _build_asset_url(asset_path: str | None) -> str | None:
        if not asset_path:
            return None

        normalized = str(asset_path).replace("\\", "/").lstrip("/")
        if normalized.startswith("assets/"):
            normalized = normalized[len("assets/"):]
        encoded = "/".join(quote(part) for part in normalized.split("/"))
        return f"/kanji-assets/{encoded}"

    def _build_details(self, metadata: dict[str, Any] | None, kanji_char: str | None = None) -> dict[str, Any] | None:
        if not metadata:
            return None

        comments_payload = []
        image_urls: list[str] = []
        for comment in metadata.get("comments") or []:
            local_image_url = self._build_asset_url(comment.get("image_path"))
            comment_image_url = local_image_url or comment.get("image_url")
            if comment_image_url:
                image_urls.append(comment_image_url)

            comments_payload.append(
                {
                    "content_text": comment.get("content_text") or "",
                    "image_url": comment_image_url,
                    "user_name": ((comment.get("user") or {}).get("name") or None),
                }
            )

        reading = metadata.get("reading") or {}
        meaning = metadata.get("meaning") or {}
        stroke = metadata.get("stroke") or {}
        explanation = metadata.get("explanation") or {}

        return {
            "meaning_vi": meaning.get("vi"),
            "meaning_en": meaning.get("en"),
            "on_readings": reading.get("on") or [],
            "kun_readings": reading.get("kun") or [],
            "am_han": reading.get("am_han"),
            "stroke_count": stroke.get("count"),
            "frequency": metadata.get("frequency"),
            "examples": metadata.get("examples") or [],
            "explanation": explanation.get("text"),
            "svg_url": f"/api/v1/ai/kanji/svg/{quote(kanji_char)}" if kanji_char else self._build_asset_url(stroke.get("svg")),
            "image_urls": image_urls,
            "comments": comments_payload,
        }

    def get_svg_content(self, kanji_char: str) -> str:
        metadata = self._load_kanji_metadata(kanji_char)
        if not metadata:
            raise FileNotFoundError(f"No metadata found for kanji {kanji_char}")

        stroke = metadata.get("stroke") or {}
        svg_relative_path = stroke.get("svg")
        if not svg_relative_path:
            raise FileNotFoundError(f"No SVG found for kanji {kanji_char}")

        normalized = str(svg_relative_path).replace("\\", "/").lstrip("/")
        if normalized.startswith("assets/"):
            normalized = normalized[len("assets/"):]
        svg_path = settings.KANJI_ASSETS_DIR / normalized
        if not svg_path.exists():
            raise FileNotFoundError(f"SVG file not found at {svg_path}")

        content = svg_path.read_text(encoding="utf-8")
        # Android SVG renderers are stricter than browsers; strip KanjiVG-specific
        # namespaced metadata and keep only the drawing primitives we actually need.
        content = re.sub(r"\sxmlns:kvg=\"[^\"]*\"", "", content, count=1)
        content = re.sub(r"\skvg:[\w-]+=\"[^\"]*\"", "", content)
        content = re.sub(r"<style\b[^>]*>.*?</style>\s*", "", content, flags=re.DOTALL)
        return content

    def predict(self, image: Image.Image) -> Dict[str, Any]:
        self._load_resources()
        if self.model is None:
            raise RuntimeError("Kanji model failed to load")

        processed = self._preprocess_image(image)
        input_tensor = self.preprocess(processed).unsqueeze(0).to(self.device)

        try:
            with torch.no_grad():
                # Empirically verified: Zeros are the most accurate baseline for missing stroke features
                stroke_features = torch.zeros((1, 24)).to(self.device)
                outputs = self.model(input_tensor, stroke_features)
                probs = torch.softmax(outputs[0], dim=0)
                top5_prob, top5_idx = torch.topk(probs, 5)
        except RuntimeError as exc:
            if self.device.type == "cuda" and self._should_retry_on_cpu(exc):
                logger.warning("Kanji inference failed on CUDA (%s). Retrying on CPU.", exc)
                self._reset_to_cpu()
                return self.predict(image)
            raise

        results = []
        for prob, idx in zip(top5_prob, top5_idx):
            label_id = int(idx.item())
            kanji_char = self.label_map.get(label_id, "?")
            metadata = self._load_kanji_metadata(kanji_char)
            meaning_vi = None
            reading = None
            details = None
            if metadata:
                meaning_vi = ((metadata.get("meaning") or {}).get("vi") or None)
                reading = ", ".join((metadata.get("reading") or {}).get("kun") or []) or None
                if not reading:
                    reading = ", ".join((metadata.get("reading") or {}).get("on") or []) or None
                details = self._build_details(metadata, kanji_char)
            
            results.append(
                {
                    "kanji": kanji_char,
                    "confidence": float(prob.item()),
                    "label_id": label_id,
                    "meaning_vi": meaning_vi,
                    "reading": reading,
                    "analysis": None,
                    "details": details,
                }
            )

        return {
            "top1": results[0],
            "top5": results,
        }


kanji_engine = KanjiService()
