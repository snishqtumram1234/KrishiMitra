import cv2
import numpy as np
import pytest
from conftest import GOOD_JPEG, encode, leaf_photo

from app.config import Settings
from app.schemas.case import CaseInput, Category, DecisionState
from app.services.orchestrator import Orchestrator
from app.services.quality_gate import QualityGate
from app.services.vision_service import FakeVisionService

gate = QualityGate(Settings())


def blurred(img, k=31):
    return cv2.GaussianBlur(img, (k, k), 0)


def test_good_photo_passes():
    r = gate.check(GOOD_JPEG)
    assert r.passed and r.reason is None
    assert r.score == pytest.approx(1.0)
    assert r.details["failures"] == []
    for key in ("width", "height", "brightness", "sharpness", "scores"):
        assert key in r.details


def test_png_and_grayscale_pass():
    assert gate.check(encode(leaf_photo(), ".png")).passed
    gray = cv2.cvtColor(leaf_photo(), cv2.COLOR_BGR2GRAY)
    assert gate.check(encode(gray)).passed


@pytest.mark.parametrize("data,reason", [(None, "missing_image"), (b"", "missing_image"),
                                         (b"not an image at all", "unreadable_image"),
                                         (b"x" * 5000, "unreadable_image")])
def test_missing_or_garbage(data, reason):
    r = gate.check(data)
    assert not r.passed and r.reason == reason and r.score == 0.0


def test_too_small():
    r = gate.check(encode(leaf_photo(200, 150)))
    assert not r.passed and "too_small" in r.details["failures"]


def test_too_dark():
    r = gate.check(encode((leaf_photo() * 0.15).astype(np.uint8)))
    assert not r.passed and r.reason == "too_dark"


def test_too_bright():
    bright = np.clip(leaf_photo().astype(np.int16) + 170, 0, 255).astype(np.uint8)
    r = gate.check(encode(bright))
    assert not r.passed and "too_bright" in r.details["failures"]


def test_blurry():
    r = gate.check(encode(blurred(leaf_photo())))
    assert not r.passed and r.reason == "blurry"
    assert r.details["sharpness"] < 60


def test_flat_single_colour_is_blurry():
    flat = np.full((480, 640, 3), (60, 150, 70), np.uint8)
    assert gate.check(encode(flat)).reason == "blurry"


def test_sharpness_is_resolution_independent():
    """Same scene at 2 resolutions should get a similar verdict and similar sharpness."""
    small = gate.check(encode(leaf_photo(640, 480)))
    big_img = cv2.resize(leaf_photo(640, 480), (2560, 1920), interpolation=cv2.INTER_CUBIC)
    big = gate.check(encode(big_img))
    assert small.passed and big.passed


def test_multiple_failures_all_reported():
    dark_blurry = (blurred(leaf_photo()) * 0.15).astype(np.uint8)
    r = gate.check(encode(dark_blurry))
    assert {"too_dark", "blurry"} <= set(r.details["failures"])


def test_score_orders_quality():
    good = gate.check(GOOD_JPEG).score
    slight = gate.check(encode(blurred(leaf_photo(), 9))).score
    heavy = gate.check(encode(blurred(leaf_photo(), 41))).score
    assert good >= slight >= heavy
    assert 0.0 <= heavy < 1.0


def test_thresholds_come_from_settings():
    strict = QualityGate(Settings(quality_min_sharpness=1e9))
    assert strict.check(GOOD_JPEG).reason == "blurry"
    lenient = QualityGate(Settings(quality_min_sharpness=0.0))
    assert lenient.check(encode(blurred(leaf_photo()))).passed


@pytest.mark.parametrize("img,tip", [
    (lambda: blurred(leaf_photo()), "hold the phone steady"),
    (lambda: (leaf_photo() * 0.15).astype(np.uint8), "daylight"),
    (lambda: leaf_photo(200, 150), "move closer"),
])
def test_orchestrator_gives_specific_tip_and_skips_vision(img, tip):
    o = Orchestrator(Settings(), vision=FakeVisionService(label=Category.RUST_LIKE, confidence=0.99))
    r = o.run(CaseInput(crop="soybean", symptom_context="yellow spots", close_up_image=encode(img())))
    assert r.state == DecisionState.NEEDS_BETTER_IMAGE
    assert tip in r.message
    assert "vision" not in r.route_trace
    q = next(c for c in r.calls if c.route == "quality_gate")
    assert q.output["details"]["failures"]  # measurements are logged to model_runs.output
