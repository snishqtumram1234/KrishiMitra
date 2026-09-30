"""PLACEHOLDER vision model. Returns a random label and confidence.

Replace with the real ONNX soybean classifier later. Interface: predict(image) -> list[VisionResult]
(one entry per specialist model, so the orchestrator can detect conflicting models).
"""

import random

from app.schemas.case import Category
from app.schemas.orchestration import VisionResult


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
