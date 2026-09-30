"""Image-quality gate (OpenCV). Runs before any model sees the photo.

Checks, in order: decodable -> resolution -> brightness/exposure -> sharpness (blur).
Sharpness is measured on a copy resized to a fixed long side so the threshold does not
depend on camera resolution. Thresholds are initial guesses; calibrate with
`python -m app.services.quality_gate <images...>` on real farmer photos.

Usage for calibration:
  python -m app.services.quality_gate photo1.jpg photo2.jpg
"""

import json
import sys

import cv2
import numpy as np

from app.config import Settings, get_settings
from app.schemas.orchestration import QualityResult

ANALYSIS_LONG_SIDE = 512


def _ratio(value: float, threshold: float) -> float:
    """value/threshold clamped to [0,1]; a threshold <= 0 disables the check (score 1)."""
    if threshold <= 0:
        return 1.0
    return max(0.0, min(1.0, value / threshold))


def _measure(gray: np.ndarray) -> dict:
    h, w = gray.shape
    scale = ANALYSIS_LONG_SIDE / max(h, w)
    small = cv2.resize(gray, (max(1, round(w * scale)), max(1, round(h * scale))), interpolation=cv2.INTER_AREA)
    return {
        "width": int(w),
        "height": int(h),
        "brightness": round(float(gray.mean()), 1),
        "dark_fraction": round(float((gray <= 10).mean()), 3),
        "bright_fraction": round(float((gray >= 245).mean()), 3),
        "sharpness": round(float(cv2.Laplacian(small, cv2.CV_64F).var()), 1),
    }


class QualityGate:
    model_name = "opencv-quality-gate"

    def __init__(self, settings: Settings | None = None):
        s = settings or get_settings()
        self.min_side = s.quality_min_side
        self.min_brightness = s.quality_min_brightness
        self.max_brightness = s.quality_max_brightness
        self.max_clipped_fraction = s.quality_max_clipped_fraction
        self.min_sharpness = s.quality_min_sharpness

    def check(self, image: bytes | None) -> QualityResult:
        if not image:
            return QualityResult(passed=False, score=0.0, reason="missing_image")
        gray = cv2.imdecode(np.frombuffer(image, np.uint8), cv2.IMREAD_GRAYSCALE)
        if gray is None or gray.size == 0:
            return QualityResult(passed=False, score=0.0, reason="unreadable_image")

        m = _measure(gray)
        # Sub-scores in [0,1]; 1.0 means the check passes comfortably.
        scores = {
            "resolution": _ratio(min(m["width"], m["height"]), self.min_side),
            "exposure": self._exposure_score(m),
            "sharpness": _ratio(m["sharpness"], self.min_sharpness),
        }
        failures = self._failures(m)
        return QualityResult(
            passed=not failures,
            score=round(min(scores.values()), 3),
            reason=failures[0] if failures else None,
            details={**m, "failures": failures, "scores": {k: round(v, 3) for k, v in scores.items()}},
        )

    def _failures(self, m: dict) -> list[str]:
        f = []
        if min(m["width"], m["height"]) < self.min_side:
            f.append("too_small")
        if m["brightness"] < self.min_brightness or m["dark_fraction"] > self.max_clipped_fraction:
            f.append("too_dark")
        if m["brightness"] > self.max_brightness or m["bright_fraction"] > self.max_clipped_fraction:
            f.append("too_bright")
        if m["sharpness"] < self.min_sharpness:
            f.append("blurry")
        return f

    def _exposure_score(self, m: dict) -> float:
        b = m["brightness"]
        if b < self.min_brightness:
            s = _ratio(b, self.min_brightness)
        elif b > self.max_brightness:
            s = _ratio(255 - b, 255 - self.max_brightness)
        else:
            s = 1.0
        clipped = max(m["dark_fraction"], m["bright_fraction"])
        if clipped > self.max_clipped_fraction:
            s = min(s, _ratio(self.max_clipped_fraction, clipped))
        return max(0.0, min(1.0, s))


if __name__ == "__main__":
    gate = QualityGate()
    for path in sys.argv[1:]:
        with open(path, "rb") as f:
            r = gate.check(f.read())
        print(json.dumps({"file": path, "passed": r.passed, "score": r.score, "reason": r.reason, **(r.details or {})}))
