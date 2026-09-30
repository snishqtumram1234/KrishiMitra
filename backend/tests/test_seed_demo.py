"""The demo dataset and seed script must stay in sync with the router and quality gate."""

import importlib.util
import json
import uuid
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from test_weather_service import open_meteo_payload

from app.api.deps import get_orchestrator, get_store
from app.config import Settings, get_settings
from app.main import app
from app.schemas.case import Category
from app.services.case_store import InMemoryCaseStore
from app.services.orchestrator import Orchestrator
from app.services.quality_gate import QualityGate
from app.services.vision_service import FakeVisionService
from app.services.weather_service import MemoryWeatherSnapshots, WeatherService

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("seed_demo", ROOT / "backend" / "scripts" / "seed_demo.py")
seed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seed)

CASES = json.loads((ROOT / "data" / "demo-cases" / "cases.json").read_text(encoding="utf-8"))["cases"]
SECRET = "test-secret-at-least-32-bytes-long!!"
gate = QualityGate(Settings())


def test_dataset_size_and_shape():
    assert 30 <= len(CASES) <= 50
    assert len({c["id"] for c in CASES}) == len(CASES)
    assert {c["language"] for c in CASES} == {"en", "mr"}
    for c in CASES:
        assert c["symptom_context"].strip() and c["district"]


@pytest.mark.parametrize("style", ["healthy", "rust", "spots", "holes", "mixed"])
def test_good_synthetic_styles_pass_the_quality_gate(style):
    for seed_no in range(3):
        assert gate.check(seed.synthetic_image(style, seed_no)).passed, (style, seed_no)


@pytest.mark.parametrize("style,issue", [("blurry", "blurry"), ("dark", "too_dark"), ("tiny", "too_small"),
                                         ("no_leaf", "no_leaf_detected"), ("overexposed", "too_bright")])
def test_bad_synthetic_styles_fail_for_the_intended_reason(style, issue):
    r = gate.check(seed.synthetic_image(style, 1))
    assert not r.passed and issue in r.issues, (style, r.issues)


def test_unknown_style_is_rejected():
    with pytest.raises(ValueError):
        seed.synthetic_image("purple", 0)


def test_every_demo_image_style_is_known():
    styles = set()
    for c in CASES:
        for spec_ in (c.get("image"), c.get("field_overview"), (c.get("follow_up") or {}).get("image")):
            if spec_ and "style" in spec_:
                styles.add(spec_["style"])
    for s in styles:
        seed.synthetic_image(s, 0)


def test_demo_cases_match_their_expectations_end_to_end():
    """Run all demo cases through the real API routes in-process; vision is faked (output not asserted)."""
    store = InMemoryCaseStore()
    weather = WeatherService(Settings(weather_live_enabled=True), snapshots=MemoryWeatherSnapshots(),
                             client=httpx.Client(transport=httpx.MockTransport(
                                 lambda req: httpx.Response(200, json=open_meteo_payload()))))
    orch = Orchestrator(Settings(), vision=FakeVisionService(label=Category.RUST_LIKE, confidence=0.95),
                        weather=weather)
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_orchestrator] = lambda: orch
    app.dependency_overrides[get_settings] = lambda: Settings(supabase_jwt_secret=SECRET)
    try:
        client = TestClient(app)
        api = seed.Api("http://test", client=client)
        farmer = seed.token(str(uuid.uuid4()), SECRET)
        wrong = []
        for i, case in enumerate(CASES):
            res = seed.run_case(api, case, farmer, i)
            if miss := seed.mismatches(case, res):
                wrong.append((case["id"], miss))
        assert wrong == []

        expert = seed.token(str(uuid.uuid4()), SECRET, expert=True)
        o = client.get("/api/metrics/overview", headers=expert).json()
        assert o["total_cases"] == len(CASES)
        assert o["total_analyses"] == len(CASES) + sum(1 for c in CASES if c.get("follow_up"))
        r = client.get("/api/metrics/routes", headers=expert).json()
        assert {p["path"] for p in r["by_path"]} >= {"image_diagnosis", "weather", "treatment_safety",
                                                     "expert_escalation", "unsupported_request", "advisory_lookup",
                                                     "general_crop_question"}
        # bad photos, weather, treatment, expert, unsupported and advisory questions never reached vision
        assert r["vision_call_rate"]["rate"] < 0.5 and r["estimated_cost_saved_usd"] > 0
    finally:
        app.dependency_overrides.clear()
