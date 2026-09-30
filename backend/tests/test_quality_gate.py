import cv2
import numpy as np
import pytest
from conftest import GOOD_JPEG, encode, leaf_photo

from app.config import Settings
from app.schemas.case import CaseInput, Category, DecisionState
from app.services.orchestrator import Orchestrator
from app.services.quality_gate import NEXT_ACTION, QualityGate
from app.services.vision_service import FakeVisionService

gate = QualityGate(Settings())


def blurry():
    return cv2.GaussianBlur(leaf_photo(), (31, 31), 0)


def dark():
    return (leaf_photo() * 0.15).astype(np.uint8)


def not_a_leaf(w=640, h=480):
    """Sharp, well-exposed, but grey/blue: e.g. a photo of a wall, sky or soil."""
    rng = np.random.default_rng(1)
    img = np.full((h, w, 3), (150, 120, 110), np.float32) + rng.normal(0, 25, (h, w, 3))
    return np.clip(img, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- the three required cases
def test_good_image_passes():
    r = gate.check(GOOD_JPEG)
    assert r.passed and r.issues == [] and r.next_action == "continue"
    assert r.score == 100
    for key in ("width", "height", "brightness", "sharpness", "leaf_ratio", "sub_scores"):
        assert key in r.details


def test_blurry_image_fails():
    r = gate.check(encode(blurry()))
    assert not r.passed
    assert r.issues == ["blurry"] and r.next_action == "retake_steady"
    assert r.score < 20
    assert r.details["sharpness"] < 60


def test_dark_image_fails():
    r = gate.check(encode(dark()))
    assert not r.passed
    assert r.issues[0] == "too_dark" and r.next_action == "retake_in_daylight"
    assert r.details["brightness"] < 40


# ---------------------------------------------------------------- leaf presence
def test_non_leaf_photo_fails_leaf_presence():
    r = gate.check(encode(not_a_leaf()))
    assert "no_leaf_detected" in r.issues and r.next_action == "retake_leaf_in_frame"
    assert r.details["leaf_ratio"] < 0.10
    assert "blurry" not in r.issues  # it is sharp; only the leaf check fails


def test_yellowed_leaf_still_counts_as_leaf():
    """Chlorotic / rust-affected leaves are yellow-green; they must not be rejected as 'no leaf'."""
    rng = np.random.default_rng(2)
    yellowish = np.clip(np.full((480, 640, 3), (40, 180, 190), np.float32) + rng.normal(0, 18, (480, 640, 3)),
                        0, 255).astype(np.uint8)  # BGR yellow
    r = gate.check(encode(yellowish))
    assert "no_leaf_detected" not in r.issues


def test_grayscale_photo_has_no_leaf_signal():
    gray = cv2.cvtColor(leaf_photo(), cv2.COLOR_BGR2GRAY)
    assert gate.check(encode(gray)).issues == ["no_leaf_detected"]


# ---------------------------------------------------------------- other checks
def test_png_passes():
    assert gate.check(encode(leaf_photo(), ".png")).passed


@pytest.mark.parametrize("data,issue", [(None, "missing_image"), (b"", "missing_image"),
                                        (b"not an image at all", "unreadable_image"),
                                        (b"x" * 5000, "unreadable_image")])
def test_missing_or_garbage(data, issue):
    r = gate.check(data)
    assert not r.passed and r.issues == [issue] and r.score == 0 and r.next_action == "upload_image"


def test_too_small():
    r = gate.check(encode(leaf_photo(200, 150)))
    assert "too_small" in r.issues and r.next_action == "retake_closer"


def test_too_bright():
    bright = np.clip(leaf_photo().astype(np.int16) + 170, 0, 255).astype(np.uint8)
    assert "too_bright" in gate.check(encode(bright)).issues


def test_all_issues_reported_first_one_drives_next_action():
    r = gate.check(encode((blurry() * 0.15).astype(np.uint8)))
    assert {"too_dark", "blurry"} <= set(r.issues)
    assert r.next_action == NEXT_ACTION[r.issues[0]]


def test_every_issue_has_a_next_action():
    assert {"missing_image", "unreadable_image", "too_small", "too_dark", "too_bright", "blurry",
            "no_leaf_detected"} == set(NEXT_ACTION)


def test_score_is_0_to_100_and_orders_quality():
    good = gate.check(GOOD_JPEG).score
    slight = gate.check(encode(cv2.GaussianBlur(leaf_photo(), (9, 9), 0))).score
    heavy = gate.check(encode(blurry())).score
    assert 100 >= good >= slight >= heavy >= 0
    assert all(isinstance(s, int) for s in (good, slight, heavy))


def test_sharpness_is_resolution_independent():
    big = cv2.resize(leaf_photo(640, 480), (2560, 1920), interpolation=cv2.INTER_CUBIC)
    assert gate.check(encode(leaf_photo())).passed and gate.check(encode(big)).passed


def test_thresholds_come_from_config():
    assert QualityGate(Settings(quality_min_sharpness=1e9)).check(GOOD_JPEG).issues == ["blurry"]
    assert QualityGate(Settings(quality_min_sharpness=0.0)).check(encode(blurry())).passed
    assert QualityGate(Settings(quality_min_leaf_ratio=0.0)).check(encode(not_a_leaf())).passed


# ---------------------------------------------------------------- orchestrator: vision never runs on bad images
def run(img_bytes):
    o = Orchestrator(Settings(), vision=FakeVisionService(label=Category.RUST_LIKE, confidence=0.99))
    return o.run(CaseInput(crop="soybean", symptom_context="yellow spots", close_up_image=img_bytes))


@pytest.mark.parametrize("make,tip", [
    (blurry, "hold the phone steady"),
    (dark, "daylight"),
    (lambda: leaf_photo(200, 150), "move closer"),
    (not_a_leaf, "fill most of the frame"),
], ids=["blurry", "dark", "small", "no_leaf"])
def test_bad_image_stops_before_vision(make, tip):
    r = run(encode(make()))
    assert r.state == DecisionState.NEEDS_BETTER_IMAGE
    assert tip in r.message
    assert [c.route for c in r.calls] == ["quality_gate"]
    assert r.skipped_steps == ["intent_router", "vision", "advisory", "weather"]
    assert r.estimated_cost_saved_usd > 0  # the vision call we did not pay for
    q = r.calls[0]
    assert q.output["issues"] and q.output["next_action"].startswith("retake")
    assert 0 <= q.confidence <= 1  # stored in the 0-1 confidence column


def test_good_image_reaches_vision():
    r = run(GOOD_JPEG)
    assert "vision" in [c.route for c in r.calls]
    assert "vision" not in r.skipped_steps
