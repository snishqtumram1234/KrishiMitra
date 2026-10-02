"""Shared test setup: no live network calls, and synthetic photos for the OpenCV quality gate."""

import os

os.environ["WEATHER_LIVE_ENABLED"] = "false"  # tests that need "live" inject a mock HTTP transport
os.environ["ADVISORY_EXCERPTS_PATH"] = ""  # real excerpts are for the running app; tests inject their own sources
os.environ["ALLOW_DEMO_SOURCES"] = "true"  # most tests exercise guidance; strict mode is tested explicitly

import cv2
import numpy as np


def leaf_photo(w: int = 640, h: int = 480, seed: int = 0) -> np.ndarray:
    """Well-exposed, in-focus, leaf-like BGR image: green base, texture, vein lines."""
    rng = np.random.default_rng(seed)
    img = np.zeros((h, w, 3), np.float32)
    img[:] = (50, 140, 60)  # BGR green
    img += rng.normal(0, 18, img.shape)
    for x in range(0, w, 40):
        cv2.line(img, (x, 0), (w // 2, h // 2), (90, 190, 110), 2)
    return np.clip(img, 0, 255).astype(np.uint8)


def encode(img: np.ndarray, ext: str = ".jpg") -> bytes:
    ok, buf = cv2.imencode(ext, img)
    assert ok
    return buf.tobytes()


GOOD_JPEG = encode(leaf_photo())
