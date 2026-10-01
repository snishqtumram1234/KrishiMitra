from conftest import GOOD_JPEG
import random

import pytest

from app.config import Settings
from app.schemas.case import Category, CaseInput, DecisionState
from app.schemas.orchestration import AdvisoryResult, AdvisorySource, VisionResult, WeatherResult
from app.services.advisory_service import AdvisoryService
from app.services.orchestrator import Orchestrator
from app.services.vision_service import FakeVisionService
from app.services.weather_service import WeatherService

IMG = GOOD_JPEG


def case(**kw) -> CaseInput:
    base = dict(crop="soybean", symptom_context="yellow spots on leaves", close_up_image=IMG)
    base.update(kw)
    return CaseInput(**base)


def orch(conf: float, label: Category = Category.RUST_LIKE, **kw) -> Orchestrator:
    return Orchestrator(Settings(), vision=FakeVisionService(label=label, confidence=conf), **kw)


def test_poor_image_needs_better_image_and_skips_vision():
    r = orch(0.95).run(case(close_up_image=b"tiny"))
    assert r.state == DecisionState.NEEDS_BETTER_IMAGE
    assert "vision" not in r.route_trace


def test_missing_image():
    r = orch(0.95).run(case(close_up_image=None))
    assert r.state == DecisionState.NEEDS_BETTER_IMAGE


def test_non_soybean_unsupported():
    r = orch(0.95).run(case(crop="cotton"))
    assert r.state == DecisionState.UNSUPPORTED
    assert "vision" not in r.route_trace


def test_unclear_text_without_photo_needs_context():
    r = orch(0.95).run(case(symptom_context="hello", close_up_image=None))
    assert r.state == DecisionState.NEEDS_MORE_CONTEXT
    assert r.follow_up_question
    assert "vision" not in r.route_trace


def test_unclear_text_with_photo_goes_to_image_path():
    r = orch(0.95).run(case(symptom_context="hello"))
    assert r.intent_rule == "fallback:photo_attached" and r.path == "image_diagnosis"
    assert "vision" in r.route_trace


def test_marathi_intent_matches():
    r = orch(0.95).run(case(symptom_context="पानांवर पिवळे डाग"))
    assert r.state == DecisionState.PRELIMINARY_GUIDANCE


def test_low_confidence_requests_evidence_then_escalates():
    r = orch(0.30).run(case())
    assert r.state == DecisionState.NEEDS_MORE_CONTEXT
    assert r.follow_up_question
    assert "advisory" not in r.route_trace
    r = orch(0.30).run(case(field_overview_image=IMG))
    assert r.state == DecisionState.EXPERT_REVIEW


def test_mid_confidence_advisory_no_weather_one_followup_no_treatment():
    r = orch(0.70).run(case())
    assert r.state == DecisionState.PRELIMINARY_GUIDANCE
    assert r.reason == "mid_confidence"
    assert "advisory" in r.route_trace and "weather" not in r.route_trace
    assert r.follow_up_question
    assert "No treatment" in r.message


def test_high_confidence_uses_advisory_and_weather():
    r = orch(0.95).run(case())
    assert r.state == DecisionState.PRELIMINARY_GUIDANCE
    assert r.reason == "high_confidence"
    assert "advisory" in r.route_trace and "weather" in r.route_trace
    assert "not a confirmed diagnosis" in r.message
    assert r.sources


def test_boundaries():
    assert orch(0.60).run(case()).reason == "mid_confidence"
    assert orch(0.85).run(case()).reason == "mid_confidence"
    assert orch(0.5999).run(case()).state == DecisionState.NEEDS_MORE_CONTEXT
    assert orch(0.8501).run(case()).reason == "high_confidence"


def test_unknown_label_escalates():
    r = orch(0.95, label=Category.UNKNOWN).run(case())
    assert r.state == DecisionState.EXPERT_REVIEW


def test_conflicting_models_escalate():
    class Conflicting(FakeVisionService):
        def predict(self, image):
            return [
                VisionResult(model_name="a", label=Category.RUST_LIKE, confidence=0.9),
                VisionResult(model_name="b", label=Category.LEAF_SPOT_LIKE, confidence=0.9),
            ]

    r = Orchestrator(Settings(), vision=Conflicting()).run(case())
    assert r.state == DecisionState.EXPERT_REVIEW
    assert r.reason == "models_conflict"


def test_stale_advisory_escalates():
    class Stale(AdvisoryService):
        def retrieve(self, label, district):
            return AdvisoryResult(
                sources=[AdvisorySource(title="t", publisher="p", verified=True, source_type="ingested", stale=True)]
            )

    r = orch(0.95, advisory=Stale()).run(case())
    assert r.state == DecisionState.EXPERT_REVIEW


def test_advisory_error_escalates():
    class Boom(AdvisoryService):
        def retrieve(self, label, district):
            raise RuntimeError("down")

    r = orch(0.70, advisory=Boom()).run(case())
    assert r.state == DecisionState.EXPERT_REVIEW
    assert any(c.route == "advisory" and c.outcome == "error" for c in r.calls)


def test_weather_unavailable_at_high_confidence_escalates():
    class NoWeather(WeatherService):
        def get(self, district):
            return WeatherResult(available=False)

    assert orch(0.95, weather=NoWeather()).run(case()).state == DecisionState.EXPERT_REVIEW
    # mid tier does not need weather
    assert orch(0.70, weather=NoWeather()).run(case()).state == DecisionState.PRELIMINARY_GUIDANCE


def test_every_call_is_logged():
    r = orch(0.95).run(case())
    assert [c.route for c in r.calls] == ["intent_router", "quality_gate", "vision", "advisory", "weather"]
    assert all(c.outcome == "ok" and c.latency_ms >= 0 for c in r.calls)
    vision = next(c for c in r.calls if c.route == "vision")
    assert vision.confidence == pytest.approx(0.95)


def test_random_fake_vision_always_yields_valid_decision():
    for seed in range(200):
        o = Orchestrator(Settings(), vision=FakeVisionService(rng=random.Random(seed)))
        r = o.run(case(field_overview_image=IMG if seed % 2 else None))
        assert r.state in set(DecisionState)
        assert r.calls and r.route_trace[-1].startswith("decision:")
