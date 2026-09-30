"""Image-quality gate (OpenCV). Runs before any model sees the photo; a failed gate means the
vision model is never called.

Checks: decodable -> dimensions -> brightness/exposure -> sharpness (Laplacian variance) ->
leaf presence (share of plant-coloured pixels). Measurements are taken on a copy resized to a
fixed long side, so thresholds do not depend on camera resolution. Thresholds live in config.py
and are initial guesses; calibrate on real farmer photos with:

  python -m app.services.quality_gate photo1.jpg photo2.jpg
"""

import json
import sys

import cv2
import numpy as np

from app.config import Settings, get_settings
from app.schemas.orchestration import QualityResult

ANALYSIS_LONG_SIDE = 512
# "Plant-coloured" in OpenCV HSV (H is 0-180): yellow-green through green, not grey/washed out.
# Starts at yellow so chlorotic and rust-affected leaves still count as leaf.
PLANT_HUE = (20, 90)
PLANT_MIN_SATURATION = 40
PLANT_MIN_VALUE = 40

NEXT_ACTION = {
    "missing_image": "upload_image",
    "unreadable_image": "upload_image",
    "too_small": "retake_closer",
    "too_dark": "retake_in_daylight",
    "too_bright": "retake_avoid_glare",
    "blurry": "retake_steady",
    "no_leaf_detected": "retake_leaf_in_frame",
}


def _ratio(value: float, threshold: float) -> float:
    """value/threshold clamped to [0,1]; a threshold <= 0 disables the check (score 1)."""
    if threshold <= 0:
        return 1.0
    return max(0.0, min(1.0, value / threshold))


def _measure(bgr: np.ndarray) -> dict:
    h, w = bgr.shape[:2]
    scale = ANALYSIS_LONG_SIDE / max(h, w)
    small = cv2.resize(bgr, (max(1, round(w * scale)), max(1, round(h * scale))), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    plant = (
        (hsv[..., 0] >= PLANT_HUE[0]) & (hsv[..., 0] <= PLANT_HUE[1])
        & (hsv[..., 1] >= PLANT_MIN_SATURATION) & (hsv[..., 2] >= PLANT_MIN_VALUE)
    )
    return {
        "width": int(w),
        "height": int(h),
        "brightness": round(float(gray.mean()), 1),
        "dark_fraction": round(float((gray <= 10).mean()), 3),
        "bright_fraction": round(float((gray >= 245).mean()), 3),
        "sharpness": round(float(cv2.Laplacian(gray, cv2.CV_64F).var()), 1),
        "leaf_ratio": round(float(plant.mean()), 3),
    }


def _failed(issue: str) -> QualityResult:
    return QualityResult(passed=False, score=0, issues=[issue], next_action=NEXT_ACTION[issue])


class QualityGate:
    model_name = "opencv-quality-gate"

    def __init__(self, settings: Settings | None = None):
        s = settings or get_settings()
        self.min_side = s.quality_min_side
        self.min_brightness = s.quality_min_brightness
        self.max_brightness = s.quality_max_brightness
        self.max_clipped_fraction = s.quality_max_clipped_fraction
        self.min_sharpness = s.quality_min_sharpness
        self.min_leaf_ratio = s.quality_min_leaf_ratio

    def check(self, image: bytes | None) -> QualityResult:
        if not image:
            return _failed("missing_image")
        bgr = cv2.imdecode(np.frombuffer(image, np.uint8), cv2.IMREAD_COLOR)
        if bgr is None or bgr.size == 0:
            return _failed("unreadable_image")

        m = _measure(bgr)
        # Sub-scores in [0,1]; 1.0 means the check passes comfortably.
        sub = {
            "resolution": _ratio(min(m["width"], m["height"]), self.min_side),
            "exposure": self._exposure_score(m),
            "sharpness": _ratio(m["sharpness"], self.min_sharpness),
            "leaf_presence": _ratio(m["leaf_ratio"], self.min_leaf_ratio),
        }
        issues = self._issues(m)
        return QualityResult(
            passed=not issues,
            score=round(100 * min(sub.values())),
            issues=issues,
            next_action=NEXT_ACTION[issues[0]] if issues else "continue",
            details={**m, "sub_scores": {k: round(v, 3) for k, v in sub.items()}},
        )

    def _issues(self, m: dict) -> list[str]:
        issues = []
        if min(m["width"], m["height"]) < self.min_side:
            issues.append("too_small")
        if m["brightness"] < self.min_brightness or m["dark_fraction"] > self.max_clipped_fraction:
            issues.append("too_dark")
        if m["brightness"] > self.max_brightness or m["bright_fraction"] > self.max_clipped_fraction:
            issues.append("too_bright")
        if m["sharpness"] < self.min_sharpness:
            issues.append("blurry")
        if m["leaf_ratio"] < self.min_leaf_ratio:
            issues.append("no_leaf_detected")
        return issues

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
        print(json.dumps({"file": path, **r.model_dump()}))
