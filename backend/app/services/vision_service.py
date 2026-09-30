"""Vision specialist models. Interface: predict(image bytes) -> list[VisionResult]
(one entry per model, so the orchestrator can detect conflicting models).

OnnxVisionService runs the trained soybean classifier from ml/ (see ml/README.md for the ONNX contract).
FakeVisionService returns random output and is for tests/demos only.
"""

import io
import json
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from app.config import Settings
from app.schemas.case import Category
from app.schemas.orchestration import VisionResult

RESIZE, CROP = 256, 224  # must match ml/train.py eval_tf: Resize(256) -> CenterCrop(224)


def preprocess(image: bytes) -> np.ndarray:
    """bytes -> float32 (1,3,224,224) RGB in [0,1]. Normalisation happens inside the ONNX graph."""
    with Image.open(io.BytesIO(image)) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        w, h = im.size
        if w <= h:
            size = (RESIZE, int(RESIZE * h / w))
        else:
            size = (int(RESIZE * w / h), RESIZE)
        im = im.resize(size, Image.BILINEAR)
        w, h = im.size
        left, top = int(round((w - CROP) / 2.0)), int(round((h - CROP) / 2.0))
        im = im.crop((left, top, left + CROP, top + CROP))
        arr = np.asarray(im, dtype=np.float32) / 255.0
    return arr.transpose(2, 0, 1)[None]


class OnnxVisionService:
    model_name = "soybean-mobilenetv3-onnx"

    def __init__(self, model_path: str | Path):
        import onnxruntime as ort

        path = Path(model_path)
        meta_path = path.with_suffix(".json")
        if not path.exists() or not meta_path.exists():
            raise FileNotFoundError(
                f"Vision model not found at {path} (and {meta_path.name}). Train it with ml/ and copy "
                "the files into backend/models/, or set VISION_BACKEND=fake for development."
            )
        self.classes = [Category(c) for c in json.loads(meta_path.read_text())["classes"]]
        self._session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
        self._input = self._session.get_inputs()[0].name

    def predict(self, image: bytes) -> list[VisionResult]:
        probs = self._session.run(None, {self._input: preprocess(image)})[0][0]
        i = int(np.argmax(probs))
        return [VisionResult(model_name=self.model_name, label=self.classes[i], confidence=float(probs[i]))]


class FakeVisionService:
    model_name = "fake-vision-random"

    def __init__(
        self,
        rng: random.Random | None = None,
        label: Category | None = None,
        confidence: float | None = None,
    ):
        self._rng = rng or random.Random()
        self._label = label  # optional overrides for deterministic tests/demos
        self._confidence = confidence

    def predict(self, image: bytes) -> list[VisionResult]:
        label = self._label or self._rng.choice(list(Category))
        confidence = self._confidence if self._confidence is not None else self._rng.random()
        return [VisionResult(model_name=self.model_name, label=label, confidence=confidence)]


def make_vision_service(settings: Settings) -> OnnxVisionService | FakeVisionService:
    if settings.vision_backend == "fake":
        return FakeVisionService()
    if settings.vision_backend == "onnx":
        return OnnxVisionService(settings.vision_model_path)
    raise ValueError(f"Unknown VISION_BACKEND: {settings.vision_backend!r}")
