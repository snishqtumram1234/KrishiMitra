"""Advisory source honesty: placeholder and demo sources are NEVER verified=true.

Only a real ingested advisory document may be verified. This is enforced in the schema (a verified demo
source cannot even be constructed), in the service, in the policy, and checked end to end over the demo dataset.
"""

import json
import time
import uuid
from datetime import UTC, date, datetime
from pathlib import Path

import httpx
import pytest
from conftest import GOOD_JPEG
from fastapi.testclient import TestClient
from pydantic import ValidationError
from test_weather_service import open_meteo_payload

import jwt
from app.api.deps import get_orchestrator, get_store
from app.config import Settings, get_settings
from app.main import app
from app.schemas.case import CaseInput, Category, DecisionState
from app.schemas.orchestration import AdvisoryResult, AdvisorySource
from app.services.advisory_service import AdvisoryService
from app.services.case_store import InMemoryCaseStore
from app.services.orchestrator import Orchestrator
from app.services.vision_service import FakeVisionService
from app.services.weather_service import MemoryWeatherSnapshots, WeatherService

STRICT = Settings(allow_demo_sources=False)
DEMO_MODE = Settings(allow_demo_sources=True)
INGESTED = dict(title="ICAR soybean rust management", publisher="ICAR-IISR Indore", verified=True,
                source_type="ingested", published_at=date(2025, 6, 1), source_url="https://example.org/rust.pdf")
ROOT = Path(__file__).resolve().parents[2]


def vision(conf=0.95, label=Category.RUST_LIKE):
    return FakeVisionService(label=label, confidence=conf)


def ask(settings, conf=0.95, image=GOOD_JPEG, text="yellow spots on leaves", **kw):
    o = Orchestrator(settings, vision=vision(conf), **kw)
    return o.run(CaseInput(crop="soybean", symptom_context=text, close_up_image=image))


class IngestedAdvisory(AdvisoryService):
    """What a real ingested, reviewed advisory looks like (test double: no ingestion exists yet)."""

    def __init__(self, **overrides):
        self.src = AdvisorySource(**{**INGESTED, **overrides})

    def retrieve(self, label, district):
        return AdvisoryResult(sources=[self.src], summary="Reviewed guidance text.")

    def search(self, query, district):
        return AdvisoryResult(sources=[self.src], summary="Reviewed guidance text.")


# ---------------------------------------------------------------- the schema makes the lie impossible
def test_a_verified_demo_source_cannot_be_constructed():
    with pytest.raises(ValidationError, match="Only ingested advisory documents may be verified"):
        AdvisorySource(title="t", publisher="p", verified=True)  # source_type defaults to demo
    with pytest.raises(ValidationError, match="Only ingested"):
        AdvisorySource(title="t", publisher="p", verified=True, source_type="demo")


def test_a_verified_demo_source_cannot_be_parsed_from_json_either():
    for payload in ({"title": "t", "publisher": "p", "verified": True},
                    {"title": "t", "publisher": "p", "verified": True, "source_type": "demo"}):
        with pytest.raises(ValidationError):
            AdvisorySource.model_validate(payload)


def test_an_ingested_source_may_be_verified_and_keeps_its_dates_separate():
    s = AdvisorySource(**INGESTED)
    assert s.verified and s.source_type == "ingested"
    assert s.published_at == date(2025, 6, 1) and s.source_url == "https://example.org/rust.pdf"
    assert isinstance(s.retrieved_at, datetime) and s.retrieved_at.tzinfo is not None
    assert s.retrieved_at.date() != s.published_at  # fetched now, published long ago: never conflated


def test_sources_default_to_the_safe_side():
    s = AdvisorySource(title="t", publisher="p", verified=False)
    assert s.source_type == "demo" and s.published_at is None and s.source_url is None


# ---------------------------------------------------------------- the placeholder service
@pytest.mark.parametrize("district", ["Pune", "Latur", "Nagpur", "Unknown District"])
def test_placeholder_service_never_returns_a_verified_source(district):
    svc = AdvisoryService()
    results = [svc.retrieve(label, district) for label in Category] + [svc.search("any question", district),
                                                                       svc.treatment_sources("pesticide", district)]
    sources = [s for r in results for s in r.sources]
    assert sources, "the placeholder should return demo sources for non-treatment lookups"
    for s in sources:
        assert s.verified is False
        assert s.source_type == "demo"
        assert s.published_at is None and s.source_url is None
        assert "demo" in s.publisher.lower() and "placeholder" not in s.title.lower()
        assert s.retrieved_at.tzinfo is not None
    assert not any(r.usable for r in results)
    assert results[-1].sources == []  # treatment: no sources at all, never a made-up one


def test_demo_advisory_result_is_never_usable():
    r = AdvisoryService().retrieve(Category.RUST_LIKE, "Pune")
    assert r.demo_only and not r.usable


# ---------------------------------------------------------------- policy: strict (default) vs demo mode
def test_default_settings_are_strict():
    """The declared default is strict. (The test environment turns demo mode on via ALLOW_DEMO_SOURCES, so
    Settings() itself is not the thing to check here.)"""
    assert Settings.model_fields["allow_demo_sources"].default is False


@pytest.mark.parametrize("conf", [0.61, 0.72, 0.85, 0.86, 0.95, 0.99])
@pytest.mark.parametrize("label", [Category.HEALTHY, Category.RUST_LIKE, Category.LEAF_SPOT_LIKE, Category.INSECT_DAMAGE])
def test_strict_mode_never_gives_guidance_from_demo_sources(conf, label):
    o = Orchestrator(STRICT, vision=vision(conf, label),
                     weather=WeatherService(Settings(weather_live_enabled=False), snapshots=MemoryWeatherSnapshots()))
    r = o.run(CaseInput(crop="soybean", symptom_context="yellow spots", close_up_image=GOOD_JPEG))
    assert r.state == DecisionState.EXPERT_REVIEW
    assert r.reason == "sources_unavailable:advisory"
    assert r.preliminary_label == label and r.confidence == pytest.approx(conf)  # the observation is kept
    assert r.sources and all(s.verified is False and s.source_type == "demo" for s in r.sources)
    assert "verified_advisory_source" in r.missing_information


def test_strict_mode_text_questions_also_escalate_without_a_verified_source():
    for text in ("When should I sow soybean?", "Show me the latest KVK advisory"):
        r = ask(STRICT, text=text, image=None)
        assert r.state == DecisionState.EXPERT_REVIEW and r.reason == "sources_unavailable:advisory"


def test_demo_mode_gives_guidance_but_labels_the_source_unverified():
    r = ask(DEMO_MODE)
    assert r.state == DecisionState.PRELIMINARY_GUIDANCE
    assert "demo source and is not verified" in r.message
    assert r.sources and all(s.verified is False and s.source_type == "demo" for s in r.sources)


def test_demo_mode_never_satisfies_the_treatment_rule():
    r = ask(DEMO_MODE, text="Which pesticide and how much?", image=None)
    assert r.state == DecisionState.EXPERT_REVIEW and r.reason == "treatment_needs_expert"


def test_a_stale_demo_source_is_not_accepted_even_in_demo_mode():
    class Stale(AdvisoryService):
        def retrieve(self, label, district):
            return AdvisoryResult(sources=[AdvisorySource(title="t", publisher="p", verified=False, stale=True)])

    r = ask(DEMO_MODE, advisory=Stale())
    assert r.state == DecisionState.EXPERT_REVIEW and r.reason == "sources_unavailable:advisory"


def test_demo_mode_is_refused_in_production():
    with pytest.raises(ValidationError, match="not allowed when ENVIRONMENT=production"):
        Settings(environment="production", allow_demo_sources=True)
    assert Settings(environment="production", allow_demo_sources=False).allow_demo_sources is False


# ---------------------------------------------------------------- a real ingested source works in strict mode
def test_an_ingested_verified_source_gives_guidance_in_strict_mode_with_dates_preserved():
    r = ask(STRICT, advisory=IngestedAdvisory(),
            weather=WeatherService(Settings(weather_live_enabled=True), snapshots=MemoryWeatherSnapshots(),
                                   client=httpx.Client(transport=httpx.MockTransport(
                                       lambda req: httpx.Response(200, json=open_meteo_payload())))))
    assert r.state == DecisionState.PRELIMINARY_GUIDANCE
    s = r.sources[0]
    assert s.verified and s.source_type == "ingested"
    assert s.published_at == date(2025, 6, 1) and s.source_url == "https://example.org/rust.pdf"
    assert "demo source" not in r.message


def test_a_stale_ingested_source_is_not_used():
    r = ask(STRICT, advisory=IngestedAdvisory(stale=True))
    assert r.state == DecisionState.EXPERT_REVIEW and r.reason == "sources_unavailable:advisory"


def test_ingested_but_unverified_is_not_used_in_strict_mode():
    r = ask(STRICT, advisory=IngestedAdvisory(verified=False))
    assert r.state == DecisionState.EXPERT_REVIEW


def test_verified_flag_alone_is_not_enough_for_a_treatment_answer():
    """Treatment needs verified AND structured AND fresh."""
    r = ask(STRICT, text="Which pesticide and how much?", image=None, advisory=IngestedAdvisory(structured=False))
    assert r.state == DecisionState.EXPERT_REVIEW  # the double only answers retrieve/search; treatment stays empty


# ---------------------------------------------------------------- end to end: no verified demo source anywhere
SECRET = "test-secret-at-least-32-bytes-long!!"


def _token():
    return {"Authorization": "Bearer " + jwt.encode(
        {"sub": str(uuid.uuid4()), "aud": "authenticated", "exp": int(time.time()) + 600}, SECRET, algorithm="HS256")}


def _expert_token():
    return {"Authorization": "Bearer " + jwt.encode(
        {"sub": str(uuid.uuid4()), "aud": "authenticated", "app_metadata": {"role": "expert"},
         "exp": int(time.time()) + 600}, SECRET, algorithm="HS256")}


@pytest.mark.parametrize("settings", [STRICT, DEMO_MODE], ids=["strict", "demo_mode"])
def test_no_api_response_over_the_demo_dataset_ever_shows_a_verified_demo_source(settings):
    import importlib.util

    spec = importlib.util.spec_from_file_location("seed_demo", ROOT / "backend" / "scripts" / "seed_demo.py")
    seed = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(seed)
    cases = json.loads((ROOT / "data" / "demo-cases" / "cases.json").read_text(encoding="utf-8"))["cases"]

    store = InMemoryCaseStore()
    weather = WeatherService(Settings(weather_live_enabled=True), snapshots=MemoryWeatherSnapshots(),
                             client=httpx.Client(transport=httpx.MockTransport(
                                 lambda req: httpx.Response(200, json=open_meteo_payload()))))
    orch = Orchestrator(settings, vision=vision(0.95), weather=weather)
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_orchestrator] = lambda: orch
    app.dependency_overrides[get_settings] = lambda: Settings(supabase_jwt_secret=SECRET)
    try:
        client = TestClient(app)
        api = seed.Api("http://test", client=client)
        farmer = {"Authorization": _token()["Authorization"]}
        seen: list[dict] = []
        for i, case in enumerate(cases):
            seed.run_case(api, case, farmer, i)
        for c in client.get("/api/cases", headers=farmer).json():
            a = client.get(f"/api/cases/{c['id']}/analysis", headers=farmer)
            if a.status_code == 200:
                seen += a.json()["result"]["sources"]
        for e in client.get("/api/expert/cases", params={"status": "all"}, headers=_expert_token()).json():
            detail = client.get(f"/api/expert/cases/{e['case_id']}", headers=_expert_token()).json()
            for rec in detail["history"]:
                seen += rec["snapshot"]["sources"]
        assert seen, "the dataset should have produced sources to check"
        bad = [s for s in seen if s["verified"] and s["source_type"] != "ingested"]
        assert bad == []
        assert not any(s["verified"] for s in seen)  # and with no ingestion, nothing at all is verified
        assert all(s["source_type"] == "demo" for s in seen)
    finally:
        app.dependency_overrides.clear()


def test_metrics_retrieval_success_counts_only_verified_sources():
    from test_metrics import call, run

    from app.services import metrics_service as m

    demo = {"sources": [{"title": "t", "publisher": "p", "verified": False, "stale": False, "source_type": "demo"}]}
    real = {"sources": [{"title": "t", "publisher": "p", "verified": True, "stale": False, "source_type": "ingested"}]}
    r1, r2 = run(), run()
    o = m.overview([r1, r2], [call(r1, "advisory", output=demo), call(r2, "advisory", output=real)], m.make_window(None))
    assert (o.retrieval_success_rate.numerator, o.retrieval_success_rate.denominator) == (1, 2)
    assert any("1 of 2 advisory lookups returned demo sources only" in n for n in o.notes)
