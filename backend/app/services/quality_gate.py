"""PLACEHOLDER image-quality check. Replace with a real quality model later."""

from app.schemas.orchestration import QualityResult

MIN_IMAGE_BYTES = 1024


class QualityGate:
    model_name = "placeholder-quality-gate"

    def check(self, image: bytes | None) -> QualityResult:
        if image is None:
            return QualityResult(passed=False, score=0.0, reason="missing_image")
        if len(image) < MIN_IMAGE_BYTES:
            return QualityResult(passed=False, score=0.2, reason="image_too_small")
        return QualityResult(passed=True, score=0.9)
