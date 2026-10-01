"""Structured fields on every analysis: stable reason codes, confidence band, missing information,
follow-up options, and the full replayable trace."""

import re
import time
import uuid
from datetime import date
from pathlib import Path

import cv2
import jwt
import pytest
from conftest import GOOD_JPEG, encode, leaf_photo
from fastapi.testclient import TestClient
from test_source_honesty import INGESTED, IngestedAdvisory

from app.api.deps import get_orchestrator, get_store
from app.config import Settings, get_settings
from app.main import app
from app.schemas.case import CaseInput, Category, DecisionState
from app.schemas.orchestration import AdvisoryResult, AdvisorySource, ReasonCode, VisionResult, WeatherResult
from app.services.advisory_service import AdvisoryService
from app.services.case_store import InMemoryCaseStore
from app.services.explain import (
    FOLLOW_UP_QUESTIONS,
    MISSING_CODES,
    OPTION_TEXT,
    POSITION,
    split_reason,
    validate_follow_up_choice,
)
from app.services.orchestrator import Orchestrator
from app.services.vision_service import FakeVisionService
from app.services.weather_service import WeatherService

DEMO = Settings(allow_demo_sources=True)
STRICT = Settings(allow_demo_sources=False)
BLURRY = encode(cv2.GaussianBlur(leaf_photo(), (31, 31), 0))
SECRET = "test-secret-at-least-32-bytes-long!!"


def vision(conf=0.95, label=Category.RUST_LIKE):
    return FakeVisionService(label=label, confidence=conf)


def run(text="yellow spots on leaves", image=GOOD_JPEG, conf=0.95, label=Category.RUST_LIKE, settings=DEMO, crop="soybean",
        overview=None, **kw):
    o = Orchestrator(settings, vision=vision(conf, label), **kw)
    return o.run(CaseInput(crop=crop, symptom_context=text, close_up_image=image, field_overview_image=overview))


class NoWeather(WeatherService):
    def __init__(self):
        pass

    def get(self, district):
        return WeatherResult(available=False, district=district)


class Boom:
    model_name = "boom"

    def predict(self, image):
        raise RuntimeError("model crashed")


# ---------------------------------------------------------------- reason codes
SCENARIOS = {
    ReasonCode.QUALITY_FAILED: lambda: run(image=BLURRY),
    ReasonCode.CROP_NOT_SOYBEAN: lambda: run(crop="cotton"),
    ReasonCode.FARMER_REQUESTED_EXPERT: lambda: run("I want to talk to an expert", image=None),
    ReasonCode.UNSUPPORTED_REQUEST: lambda: run("What is the market price?", image=None),
    ReasonCode.INTENT_UNCLEAR: lambda: run("hello", image=None),
    ReasonCode.TREATMENT_NEEDS_EXPERT: lambda: run("Which pesticide and how much?", image=None),
    ReasonCode.WEATHER_CONTEXT: lambda: run("Will it rain in my area?", image=None,
                                            weather=WeatherService(Settings(weather_live_enabled=False))),
    ReasonCode.ADVISORY_LOOKUP: lambda: run("Show me the KVK advisory for soybean", image=None),
    ReasonCode.GENERAL_CROP_QUESTION: lambda: run("When should I sow soybean?", image=None),
    ReasonCode.LOW_CONFIDENCE_REQUEST_EVIDENCE: lambda: run(conf=0.3),
    ReasonCode.LOW_CONFIDENCE_ESCALATE: lambda: run(conf=0.3, overview=GOOD_JPEG),
    ReasonCode.MODELS_CONFLICT: lambda: run_conflict(),
    ReasonCode.LABEL_UNKNOWN: lambda: run(label=Category.UNKNOWN),
    ReasonCode.MID_CONFIDENCE: lambda: run(conf=0.72),
    ReasonCode.HIGH_CONFIDENCE: lambda: run(conf=0.95),
    ReasonCode.SOURCES_UNAVAILABLE: lambda: run(settings=STRICT, conf=0.72),
}


def run_conflict():
    class Conflicting(FakeVisionService):
        def predict(self, image):
            return [VisionResult(model_name="a", label=Category.RUST_LIKE, confidence=0.9),
                    VisionResult(model_name="b", label=Category.HEALTHY, confidence=0.9)]

    return Orchestrator(DEMO, vision=Conflicting()).run(
        CaseInput(crop="soybean", symptom_context="yellow spots", close_up_image=GOOD_JPEG))


def treatment_verified():
    class Structured(AdvisoryService):
        def treatment_sources(self, query, district):
            return AdvisoryResult(sources=[AdvisorySource(**{**INGESTED, "structured": True})])

    return Orchestrator(STRICT, vision=vision(), advisory=Structured()).run(
        CaseInput(crop="soybean", symptom_context="Which pesticide and how much?"))


@pytest.mark.parametrize("code", list(SCENARIOS), ids=[c.value for c in SCENARIOS])
def test_reason_code_matches_reason(code):
    r = SCENARIOS[code]()
    assert r.reason_code == code, (r.reason, r.reason_code)
    expected = r.reason_code.value + (f":{r.reason_detail}" if r.reason_detail else "")
    assert r.reason == expected.replace("quality_failed", "quality")  # the legacy string is <code>[:<detail>]
    assert (r.reason_code, r.reason_detail) == split_reason(r.reason)


def test_every_reason_code_is_reachable_and_documented_by_a_scenario():
    produced = {SCENARIOS[c]().reason_code for c in SCENARIOS} | {treatment_verified().reason_code}
    assert produced == set(ReasonCode)


def test_reason_details():
    assert run(image=BLURRY).reason_detail == "blurry"
    assert run(image=None, text="yellow spots").reason_detail == "missing_image"
    assert run(settings=STRICT, conf=0.72).reason_detail == "advisory"
    assert run(conf=0.95, weather=NoWeather()).reason_detail == "weather"
    assert Orchestrator(DEMO, vision=Boom()).run(
        CaseInput(crop="soybean", symptom_context="yellow spots", close_up_image=GOOD_JPEG)).reason_detail == "vision_error"
    assert run(conf=0.72).reason_detail is None


def test_every_reason_literal_in_the_policy_maps_to_a_code():
    src = (Path(__file__).resolve().parents[1] / "app" / "services" / "policy_engine.py").read_text(encoding="utf-8")
    for literal in set(re.findall(r'reason="([a-z_]+)"', src)):
        assert ReasonCode(literal)
    assert "quality:" in src and "sources_unavailable:" in src
    assert split_reason("quality:too_dark") == (ReasonCode.QUALITY_FAILED, "too_dark")
    with pytest.raises(ValueError):
        split_reason("made_up_reason")


# ---------------------------------------------------------------- confidence band
@pytest.mark.parametrize("conf,band", [(0.0, "low"), (0.5999, "low"), (0.60, "medium"), (0.72, "medium"),
                                       (0.85, "medium"), (0.8501, "high"), (1.0, "high")])
def test_confidence_band_boundaries(conf, band):
    assert run(conf=conf, overview=GOOD_JPEG).confidence_band == band


def test_no_confidence_means_no_band():
    assert run("Will it rain?", image=None, weather=WeatherService(Settings(weather_live_enabled=False))).confidence_band is None
    assert run(image=BLURRY).confidence_band is None  # vision never ran


def test_vision_trace_step_carries_the_band():
    v = next(s for s in run(conf=0.72).trace if s.step == "vision")
    assert v.confidence_band == "medium" and v.detail["confidence_band"] == "medium"


# ---------------------------------------------------------------- missing information
def test_missing_information_codes_are_stable_and_documented():
    for r in [SCENARIOS[c]() for c in SCENARIOS]:
        assert set(r.missing_information) <= set(MISSING_CODES)
    assert len(set(MISSING_CODES)) == len(MISSING_CODES) == 11


@pytest.mark.parametrize("result,expected", [
    (lambda: run(image=None, text="yellow spots"), ["close_up_photo"]),
    (lambda: run(image=BLURRY), ["clearer_close_up_photo"]),
    (lambda: run("hello", image=None), ["symptom_description"]),
    (lambda: run(conf=0.3), ["field_overview_photo", "growth_stage", "symptom_start_date", "recent_rainfall"]),
    (lambda: run(conf=0.72), ["affected_leaf_position", "field_overview_photo", "growth_stage", "symptom_start_date",
                              "recent_rainfall"]),
    (lambda: run(conf=0.72, overview=GOOD_JPEG), ["affected_leaf_position", "growth_stage", "symptom_start_date",
                                                  "recent_rainfall"]),
    (lambda: run(settings=STRICT, conf=0.72), ["verified_advisory_source", "field_overview_photo", "growth_stage",
                                               "symptom_start_date", "recent_rainfall"]),
    (lambda: run("Which pesticide and how much?", image=None), ["treatment_source"]),
    (lambda: run("Will it rain in my area?", image=None, weather=NoWeather()), ["current_weather"]),
    (lambda: run("I want to talk to an expert", image=None), []),
    (lambda: run("When should I sow soybean?", image=None), []),
], ids=["no_photo", "blurry", "unclear", "low_conf", "mid_conf", "mid_conf_with_overview", "no_verified_source",
        "treatment", "weather_down", "expert", "general"])
def test_missing_information(result, expected):
    assert result().missing_information == expected


def test_optional_details_the_farmer_gave_are_not_listed_as_missing():
    o = Orchestrator(DEMO, vision=vision(0.72))
    r = o.run(CaseInput(crop="soybean", symptom_context="yellow spots", close_up_image=GOOD_JPEG,
                        growth_stage="R3", symptom_started_at="2026-09-25", rainfall="heavy", field_overview_image=GOOD_JPEG))
    assert r.missing_information == ["affected_leaf_position"]


# ---------------------------------------------------------------- follow-up options
def test_follow_up_options_per_decision():
    mid = run(conf=0.72).follow_up_options
    assert (mid.question_id, mid.answer_type, mid.options) == ("leaf_position", "choice",
                                                                ["older_leaves", "younger_leaves", "both"])
    low = run(conf=0.3).follow_up_options
    assert (low.question_id, low.answer_type, low.options) == ("field_overview_photo", "photo", [])
    unclear = run("hello", image=None).follow_up_options
    assert (unclear.question_id, unclear.answer_type, unclear.options) == ("describe_problem", "text", [])
    for r in (run(conf=0.95), run(image=BLURRY), run("I want to talk to an expert", image=None)):
        assert r.follow_up_options is None


def test_follow_up_catalog_is_consistent():
    assert set(FOLLOW_UP_QUESTIONS) == {"leaf_position", "field_overview_photo", "describe_problem"}
    for (qid, opt), text in OPTION_TEXT.items():
        assert opt in FOLLOW_UP_QUESTIONS[qid][1] and text
    assert {opt for qid, (_, opts) in FOLLOW_UP_QUESTIONS.items() for opt in opts} == {o for _, o in OPTION_TEXT}


@pytest.mark.parametrize("qid,opt,ok", [
    (None, None, True), ("leaf_position", "older_leaves", True), ("leaf_position", None, True),
    ("describe_problem", None, True), ("field_overview_photo", None, True),
    (None, "older_leaves", False), ("leaf_position", "purple", False), ("nope", None, False),
    ("describe_problem", "older_leaves", False),
])
def test_validate_follow_up_choice(qid, opt, ok):
    assert (validate_follow_up_choice(qid, opt) is None) is ok


# ---------------------------------------------------------------- the trace
def steps(r):
    return {s.step: s for s in r.trace}


def test_trace_covers_every_step_in_canonical_order():
    r = run(conf=0.95, weather=WeatherService(Settings(weather_live_enabled=False)))
    assert [s.step for s in r.trace] == ["intent_router", "quality_gate", "vision", "advisory", "weather", "policy_decision"]
    assert [s.position for s in r.trace] == list(range(6)) == [POSITION[s.step] for s in r.trace]
    assert all(s.status == "completed" and s.outcome == "ok" for s in r.trace)


def test_trace_timings_are_real_and_ordered():
    r = run(conf=0.95, weather=WeatherService(Settings(weather_live_enabled=False)))
    ran = [s for s in r.trace if s.step != "policy_decision"]
    for a, b in zip(ran, ran[1:]):
        assert a.started_at_ms is not None and b.started_at_ms >= a.started_at_ms + a.latency_ms - 1
    last = ran[-1]
    policy = r.trace[-1]
    assert policy.started_at_ms >= last.started_at_ms + last.latency_ms - 1
    assert sum(s.latency_ms or 0 for s in r.trace) == r.total_latency_ms
    assert sum(s.cost_usd for s in r.trace) == pytest.approx(r.total_cost_usd)


def test_trace_details_are_codes_and_numbers():
    r = run(conf=0.72)
    t = steps(r)
    assert t["intent_router"].detail["intent"] == "crop_health_image" and t["intent_router"].detail["matched"]
    q = t["quality_gate"].detail
    assert q["passed"] is True and q["score"] == 100 and q["issues"] == [] and q["next_action"] == "continue"
    assert {"width", "height", "sharpness", "brightness", "leaf_ratio"} <= set(q["details"])
    assert t["vision"].detail["label"] == "rust_like" and t["vision"].detail["model_count"] == 1
    assert t["advisory"].detail == {"source_count": 1, "verified_count": 0, "demo_count": 1}
    p = t["policy_decision"].detail
    assert p == {"state": "PRELIMINARY_GUIDANCE", "reason_code": "mid_confidence", "reason_detail": None,
                 "confidence_band": "medium"}


@pytest.mark.parametrize("make,skipped", [
    (lambda: run(image=BLURRY), {"vision": "stopped_earlier", "advisory": "stopped_earlier", "weather": "stopped_earlier"}),
    (lambda: run(conf=0.72), {"weather": "confidence_not_high"}),
    (lambda: run(conf=0.3), {"advisory": "stopped_earlier", "weather": "stopped_earlier"}),
    (lambda: run("Will it rain in my area?", image=None, weather=WeatherService(Settings(weather_live_enabled=False))),
     {"quality_gate": "route_does_not_use_step", "vision": "route_does_not_use_step", "advisory": "route_does_not_use_step"}),
    (lambda: run("Which pesticide and how much?", image=None),
     {"quality_gate": "route_does_not_use_step", "vision": "route_does_not_use_step", "weather": "route_does_not_use_step"}),
    (lambda: run("I want to talk to an expert", image=None),
     {s: "stopped_earlier" for s in ("quality_gate", "vision", "advisory", "weather")}),
    (lambda: run(crop="cotton"), {s: "stopped_earlier" for s in ("intent_router", "quality_gate", "vision", "advisory", "weather")}),
], ids=["bad_photo", "mid", "low", "weather_route", "treatment_route", "expert_route", "wrong_crop"])
def test_skipped_steps_say_why(make, skipped):
    r = make()
    t = steps(r)
    got = {s: t[s].skipped_reason for s in t if t[s].status == "skipped"}
    assert got == skipped
    assert set(got) == set(r.skipped_steps)
    for s in t.values():
        if s.status == "skipped":
            assert s.started_at_ms is None and s.latency_ms is None and s.outcome is None and s.cost_usd == 0
    assert t["policy_decision"].status == "completed"  # the decision always happens


def test_a_failed_step_is_recorded_as_failed_with_its_error():
    r = Orchestrator(DEMO, vision=Boom()).run(CaseInput(crop="soybean", symptom_context="yellow spots", close_up_image=GOOD_JPEG))
    v = steps(r)["vision"]
    assert v.status == "failed" and v.outcome == "error" and "model crashed" in v.error and v.detail == {}
    assert steps(r)["advisory"].skipped_reason == "stopped_earlier"
    assert r.reason == "sources_unavailable:vision_error"


def test_trace_json_has_no_prose_in_details():
    r = run(conf=0.72)
    for s in r.trace:
        for v in s.detail.values():
            assert not (isinstance(v, str) and " " in v and len(v) > 40), (s.step, v)


# ---------------------------------------------------------------- through the API
def headers(sub=None):
    tok = jwt.encode({"sub": str(sub or uuid.uuid4()), "aud": "authenticated", "exp": int(time.time()) + 600},
                     SECRET, algorithm="HS256")
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture
def api():
    store = InMemoryCaseStore()
    orch = Orchestrator(DEMO, vision=vision(0.72), weather=WeatherService(Settings(weather_live_enabled=False)))
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_orchestrator] = lambda: orch
    app.dependency_overrides[get_settings] = lambda: Settings(supabase_jwt_secret=SECRET)
    c = TestClient(app)
    c.h = headers()
    c.store = store
    yield c
    app.dependency_overrides.clear()


def new_case(c, text="yellow spots on leaves", **kw):
    r = c.post("/api/cases", json={"crop": "soybean", "symptom_context": text, **kw}, headers=c.h)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def upload(c, cid, kind="leaf_closeup", data=GOOD_JPEG):
    return c.post(f"/api/cases/{cid}/images", data={"kind": kind}, files={"file": ("x.jpg", data, "image/jpeg")}, headers=c.h)


def test_analyze_and_analysis_return_the_same_structured_fields_top_level_and_in_result(api):
    cid = new_case(api)
    upload(api, cid)
    a = api.post(f"/api/cases/{cid}/analyze", headers=api.h).json()
    for body in (a, api.get(f"/api/cases/{cid}/analysis", headers=api.h).json()):
        assert body["reason_code"] == "mid_confidence" and body["reason_detail"] is None
        assert body["confidence_band"] == "medium"
        assert body["missing_information"] == ["affected_leaf_position", "field_overview_photo", "growth_stage",
                                               "symptom_start_date", "recent_rainfall"]
        assert body["follow_up_options"] == {"question_id": "leaf_position", "answer_type": "choice",
                                             "options": ["older_leaves", "younger_leaves", "both"]}
        r = body["result"]
        for k in ("reason_code", "reason_detail", "confidence_band", "missing_information", "follow_up_options", "trace"):
            assert body[k] == r[k], k
    assert api.get(f"/api/cases/{cid}/analysis", headers=api.h).json() == a  # what was analysed is what is replayed


def test_the_analyze_response_contains_the_whole_trace_for_replay(api):
    cid = new_case(api)
    upload(api, cid)
    a = api.post(f"/api/cases/{cid}/analyze", headers=api.h).json()
    t = a["trace"]
    assert [s["step"] for s in t] == ["intent_router", "quality_gate", "vision", "advisory", "weather", "policy_decision"]
    assert [s["status"] for s in t] == ["completed", "completed", "completed", "completed", "skipped", "completed"]
    assert t[4]["skipped_reason"] == "confidence_not_high"
    assert t[2]["confidence_band"] == "medium" and t[2]["model_name"] == "fake-vision-random"
    assert all(s["started_at_ms"] is not None for s in t if s["status"] != "skipped")
    run_trace = api.get(f"/api/runs/{a['routing_run_id']}", headers=api.h).json()
    assert run_trace["trace"] == t
    assert run_trace["reason_code"] == "mid_confidence" and run_trace["confidence_band"] == "medium"


def test_runs_endpoint_has_codes_for_quality_failures(api):
    cid = new_case(api)
    upload(api, cid, data=BLURRY)
    a = api.post(f"/api/cases/{cid}/analyze", headers=api.h).json()
    assert (a["reason_code"], a["reason_detail"], a["confidence_band"]) == ("quality_failed", "blurry", None)
    assert a["missing_information"] == ["clearer_close_up_photo"]
    rt = api.get(f"/api/runs/{a['routing_run_id']}", headers=api.h).json()
    assert (rt["reason_code"], rt["reason_detail"]) == ("quality_failed", "blurry")


def test_structured_follow_up_answer_is_stored_validated_and_rerun(api):
    cid = new_case(api)
    upload(api, cid)
    api.post(f"/api/cases/{cid}/analyze", headers=api.h)
    r = api.post(f"/api/cases/{cid}/follow-up", data={"question_id": "leaf_position", "option": "older_leaves"}, headers=api.h)
    assert r.status_code == 200, r.text
    fu = api.store.list_follow_ups(uuid.UUID(cid))
    assert len(fu) == 1 and (fu[0].question_id, fu[0].option, fu[0].answer) == ("leaf_position", "older_leaves", "older leaves")
    audit = next(e for e in api.store.list_audit_events(uuid.UUID(cid)) if e.event_type == "follow_up_submitted")
    assert audit.details["question_id"] == "leaf_position" and audit.details["option"] == "older_leaves"


def test_follow_up_option_plus_free_text_keeps_the_farmers_words(api):
    cid = new_case(api)
    upload(api, cid)
    api.post(f"/api/cases/{cid}/follow-up", data={"question_id": "leaf_position", "option": "both",
                                                 "answer": "mostly the lower ones"}, headers=api.h)
    fu = api.store.list_follow_ups(uuid.UUID(cid))[0]
    assert (fu.option, fu.answer) == ("both", "mostly the lower ones")


def test_text_and_photo_questions_can_be_answered_with_a_question_id(api):
    cid = new_case(api, "hello")
    r = api.post(f"/api/cases/{cid}/follow-up", data={"question_id": "describe_problem", "answer": "Will it rain?"}, headers=api.h)
    assert r.status_code == 200 and r.json()["result"]["intent"] == "weather_context"
    cid2 = new_case(api)
    upload(api, cid2)
    r = api.post(f"/api/cases/{cid2}/follow-up", data={"question_id": "field_overview_photo", "kind": "field_overview"},
                 files={"file": ("f.jpg", GOOD_JPEG, "image/jpeg")}, headers=api.h)
    assert r.status_code == 200
    assert "field_overview_photo" not in r.json()["missing_information"]  # the photo it asked for is now there


@pytest.mark.parametrize("data", [
    {"option": "older_leaves"},  # option without a question
    {"question_id": "leaf_position", "option": "purple"},
    {"question_id": "nope", "answer": "x"},
    {"question_id": "describe_problem", "option": "older_leaves"},
    {},
])
def test_bad_structured_follow_ups_are_rejected(api, data):
    cid = new_case(api)
    upload(api, cid)
    assert api.post(f"/api/cases/{cid}/follow-up", data=data, headers=api.h).status_code == 422
    assert api.store.list_follow_ups(uuid.UUID(cid)) == []


def test_expert_responses_carry_reason_codes_and_prediction_bands(api):
    api.h = headers()
    expert = {"Authorization": "Bearer " + jwt.encode(
        {"sub": str(uuid.uuid4()), "aud": "authenticated", "app_metadata": {"role": "expert"},
         "exp": int(time.time()) + 600}, SECRET, algorithm="HS256")}
    cid = new_case(api, "Which pesticide and how much?")
    api.post(f"/api/cases/{cid}/analyze", headers=api.h)
    row = api.get("/api/expert/cases", headers=expert).json()[0]
    assert (row["escalation_reason_code"], row["escalation_reason_detail"]) == ("treatment_needs_expert", None)
    detail = api.get(f"/api/expert/cases/{cid}", headers=expert).json()
    assert detail["escalation_reason_code"] == "treatment_needs_expert"
    # a vision-based escalation: the prediction carries its band
    api.app.dependency_overrides[get_orchestrator] = lambda: Orchestrator(
        STRICT, vision=vision(0.72), weather=WeatherService(Settings(weather_live_enabled=False)))
    cid2 = new_case(api)
    upload(api, cid2)
    api.post(f"/api/cases/{cid2}/analyze", headers=api.h)
    d2 = api.get(f"/api/expert/cases/{cid2}", headers=expert).json()
    v = next(p for p in d2["current"]["snapshot"]["predictions"] if p["step"] == "vision")
    assert v["confidence_band"] == "medium" and d2["escalation_reason_code"] == "sources_unavailable"
    assert d2["escalation_reason_detail"] == "advisory"
