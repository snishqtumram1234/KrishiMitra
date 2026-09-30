import io
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from app.config import Settings
from app.schemas.case import Category
from app.services.vision_service import (
    FakeVisionService,
    OnnxVisionService,
    make_vision_service,
    preprocess,
)

MODEL = Path(__file__).resolve().parent.parent / "models" / "soybean_vision.onnx"
needs_model = pytest.mark.skipif(not MODEL.exists(), reason="trained model not in backend/models/")


def jpeg(w=300, h=200, color=(40, 160, 60)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color).save(buf, "JPEG")
    return buf.getvalue()


@pytest.mark.parametrize("size", [(300, 200), (200, 300), (224, 224), (1000, 1000), (50, 40)])
def test_preprocess_shape_and_range(size):
    x = preprocess(jpeg(*size))
    assert x.shape == (1, 3, 224, 224) and x.dtype == np.float32
    assert 0.0 <= x.min() and x.max() <= 1.0


def test_preprocess_handles_grayscale_and_png():
    buf = io.BytesIO()
    Image.new("L", (100, 100), 128).save(buf, "PNG")
    assert preprocess(buf.getvalue()).shape == (1, 3, 224, 224)


def test_preprocess_rejects_garbage():
    with pytest.raises(Exception):
        preprocess(b"not an image")


def test_missing_model_fails_loudly(tmp_path):
    with pytest.raises(FileNotFoundError, match="VISION_BACKEND=fake"):
        OnnxVisionService(tmp_path / "nope.onnx")


def test_factory_selects_backend(tmp_path):
    assert isinstance(make_vision_service(Settings(vision_backend="fake")), FakeVisionService)
    with pytest.raises(FileNotFoundError):
        make_vision_service(Settings(vision_backend="onnx", vision_model_path=str(tmp_path / "x.onnx")))
    with pytest.raises(ValueError):
        make_vision_service(Settings(vision_backend="magic"))


@needs_model
def test_real_model_returns_valid_prediction():
    svc = OnnxVisionService(MODEL)
    results = svc.predict(jpeg())
    assert len(results) == 1
    r = results[0]
    assert r.label in set(Category) and 0.0 <= r.confidence <= 1.0
    assert r.model_name == svc.model_name


@needs_model
def test_real_model_is_deterministic_and_probs_sum_to_one():
    svc = OnnxVisionService(MODEL)
    img = jpeg(color=(10, 200, 30))
    assert svc.predict(img)[0] == svc.predict(img)[0]
    probs = svc._session.run(None, {svc._input: preprocess(img)})[0][0]
    assert probs.shape == (len(svc.classes),) and abs(float(probs.sum()) - 1.0) < 1e-4


@needs_model
def test_orchestrator_end_to_end_with_real_model():
    from app.schemas.case import CaseInput, DecisionState
    from app.services.orchestrator import Orchestrator

    o = Orchestrator(Settings(vision_model_path=str(MODEL)))
    r = o.run(CaseInput(crop="soybean", symptom_context="yellow spots on leaf", close_up_image=jpeg(800, 600) * 1))
    assert r.state in set(DecisionState)
    assert any(c.route == "vision" and c.outcome == "ok" for c in r.calls)
