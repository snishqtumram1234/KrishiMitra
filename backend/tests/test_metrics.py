"""Metrics: hand-computed numbers on hand-built rows, then the same through the real orchestrator + API."""

import time
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
import pytest
from conftest import GOOD_JPEG
from fastapi.testclient import TestClient

from app.api.deps import get_orchestrator, get_store
from app.config import Settings, get_settings
from app.main import app
from app.schemas.case import Category, DecisionState
from app.schemas.runs import ModelRunRecord, RoutingRunRecord
from app.services import metrics_service as m
from app.services.case_store import InMemoryCaseStore
from app.services.orchestrator import Orchestrator
from app.services.vision_service import FakeVisionService

NOW = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
WINDOW = m.make_window(None, NOW)


# ---------------------------------------------------------------- builders
def run(route="image_diagnosis", state=DecisionState.PRELIMINARY_GUIDANCE, latency=10, cost=0.0, reason="x",
        case=None, intent="crop_health_image", skipped=(), saved=0.0, created=NOW):
    return RoutingRunRecord(
        id=uuid4(), case_id=case or uuid4(), route=route, intent=intent, decision_state=state, reason=reason,
        latency_ms=latency, cost_usd=cost, outcome="ok", created_at=created,
        details={"result": {"skipped_steps": list(skipped), "estimated_cost_saved_usd": saved}},
    )


def call(r, step, latency=5, cost=0.0, output=None, outcome="ok", model="m"):
    return ModelRunRecord(id=uuid4(), routing_run_id=r.id, case_id=r.case_id, step=step, model_name=model,
                          output=output, latency_ms=latency, cost_usd=cost, outcome=outcome, created_at=r.created_at)


def vision(labels, conf=0.9):
    return [{"model_name": f"v{i}", "label": lab, "confidence": conf} for i, lab in enumerate(labels)]


GOOD_SRC = {"sources": [{"title": "t", "publisher": "p", "verified": True, "stale": False}]}


# ---------------------------------------------------------------- percentiles and rates
def test_percentiles_are_nearest_rank():
    vals = [10.0 * i for i in range(1, 11)]  # 10..100
    s = m.latency_stats(vals)
    assert (s.n, s.avg_ms, s.p50_ms, s.p95_ms, s.max_ms) == (10, 55.0, 50.0, 100.0, 100.0)
    assert m.latency_stats([7]).p95_ms == 7
    s20 = m.latency_stats(range(1, 21))
    assert (s20.p50_ms, s20.p95_ms) == (10, 19)  # ceil(0.5*20)=10th, ceil(0.95*20)=19th


def test_unsorted_input_and_empty():
    assert m.latency_stats([30, 10, 20]).p50_ms == 20
    empty = m.latency_stats([])
    assert empty.n == 0 and empty.avg_ms is None and empty.p95_ms is None


def test_rate_reports_counts_and_none_for_no_data():
    assert m.rate(1, 4).model_dump() == {"numerator": 1, "denominator": 4, "rate": 0.25}
    assert m.rate(0, 0).rate is None


def test_empty_dataset_reports_no_data_not_zero():
    o = m.overview([], [], WINDOW)
    assert o.total_cases == 0 and o.total_analyses == 0
    assert o.escalation_rate.rate is None and o.abstention_rate.rate is None
    assert o.cache_hit_rate.rate is None and o.retrieval_success_rate.rate is None
    assert o.cost_per_case_usd is None and o.latency_per_analysis.p95_ms is None
    assert m.routes([], [], WINDOW).by_path == [] and m.cost_latency([], [], WINDOW).by_step == []


# ---------------------------------------------------------------- overview on known data
def test_overview_numbers():
    c1, c2 = uuid4(), uuid4()
    runs = [
        run(latency=10, cost=0.00002, case=c1),
        run(latency=20, cost=0.00002, case=c1, state=DecisionState.EXPERT_REVIEW, reason="low_confidence_escalate"),
        run(latency=30, cost=0.0, case=c2, state=DecisionState.NEEDS_BETTER_IMAGE, reason="quality:blurry"),
        run(latency=40, cost=0.00002, case=c2, state=DecisionState.NEEDS_MORE_CONTEXT,
            reason="low_confidence_request_evidence"),
    ]
    models = [
        call(runs[0], "vision", output=vision(["rust_like"])),
        call(runs[1], "vision", output=vision(["rust_like"], 0.3)),
        call(runs[3], "vision", output=vision(["rust_like"], 0.4)),
    ]
    o = m.overview(runs, models, WINDOW)
    assert (o.total_cases, o.total_analyses) == (2, 4)
    assert o.latency_per_analysis.avg_ms == 25 and o.latency_per_analysis.p50_ms == 20
    assert o.latency_per_analysis.p95_ms == 40
    assert o.cost_total_usd == pytest.approx(0.00006)
    assert o.cost_per_case_usd == pytest.approx(0.00003)  # 2 cases
    assert o.cost_per_analysis_usd == pytest.approx(0.000015)  # 4 analyses
    assert (o.escalation_rate.numerator, o.escalation_rate.denominator) == (1, 4)
    assert o.abstention_rate.numerator == 3  # everything but the one PRELIMINARY_GUIDANCE
    # vision ran on 3 analyses; 2 of those ended low-confidence
    assert (o.vision_abstention_rate.numerator, o.vision_abstention_rate.denominator) == (2, 3)
    assert o.decision_states == {"PRELIMINARY_GUIDANCE": 1, "EXPERT_REVIEW": 1, "NEEDS_BETTER_IMAGE": 1,
                                 "NEEDS_MORE_CONTEXT": 1}


def test_retrieval_success_counts_only_usable_sources():
    rs = [run() for _ in range(5)]
    models = [
        call(rs[0], "advisory", output=GOOD_SRC),
        call(rs[1], "advisory", output={"sources": []}),  # treatment path: nothing verified
        call(rs[2], "advisory", output={"sources": [{"verified": True, "stale": True}]}),
        call(rs[3], "advisory", output={"sources": [{"verified": False}]}),
        call(rs[4], "advisory", output=None, outcome="error"),
    ]
    o = m.overview(rs, models, WINDOW)
    assert (o.retrieval_success_rate.numerator, o.retrieval_success_rate.denominator) == (1, 5)


def test_cache_hit_rate_and_weather_sources():
    rs = [run() for _ in range(5)]
    models = [call(rs[i], "weather", output={"source": s}) for i, s in enumerate(
        ["live", "live", "cached", "demo", "cached"])]
    models.append(call(rs[0], "weather", outcome="error"))
    o = m.overview(rs, models, WINDOW)
    assert (o.cache_hit_rate.numerator, o.cache_hit_rate.denominator) == (2, 6)
    assert o.weather_sources == {"live": 2, "cached": 2, "demo": 1, "error": 1}
    assert not any("cache" in n for n in o.notes)


def test_no_cache_hits_adds_an_explanatory_note():
    r = run()
    o = m.overview([r], [call(r, "weather", output={"source": "live"})], WINDOW)
    assert o.cache_hit_rate.rate == 0.0 and any("cache" in n for n in o.notes)


def test_model_disagreement_counts_runs_where_models_name_different_labels():
    rs = [run() for _ in range(3)]
    models = [
        call(rs[0], "vision", output=vision(["rust_like", "leaf_spot_like"])),
        call(rs[1], "vision", output=vision(["rust_like", "rust_like"])),
        call(rs[2], "vision", output=vision(["healthy"])),
    ]
    o = m.overview(rs, models, WINDOW)
    assert o.model_disagreement_count == 1 and not any("disagreement" in n for n in o.notes)
    solo = m.overview(rs[2:], models[2:], WINDOW)
    assert solo.model_disagreement_count == 0 and any("disagreement" in n for n in solo.notes)


# ---------------------------------------------------------------- routes
def test_route_distribution_and_skips():
    runs = [
        run("image_diagnosis", latency=50, cost=0.00002, intent="crop_health_image"),
        run("image_diagnosis", latency=70, cost=0.00002, intent="crop_health_image"),
        run("weather", latency=10, intent="weather_context", skipped=["quality_gate", "vision", "advisory"],
            saved=0.00002),
        run("weather", latency=20, intent="weather_context", skipped=["quality_gate", "vision", "advisory"],
            saved=0.00002),
        run("treatment_safety", state=DecisionState.EXPERT_REVIEW, intent="treatment_safety",
            skipped=["quality_gate", "vision", "weather"], saved=0.00002),
    ]
    models = [call(runs[0], "vision"), call(runs[1], "vision")]
    r = m.routes(runs, models, WINDOW)
    assert [(p.path, p.count) for p in r.by_path] == [("image_diagnosis", 2), ("weather", 2), ("treatment_safety", 1)]
    img = r.by_path[0]
    assert img.share == 0.4 and img.avg_latency_ms == 60 and img.avg_cost_usd == pytest.approx(0.00002)
    assert r.by_intent == {"crop_health_image": 2, "weather_context": 2, "treatment_safety": 1}
    assert (r.vision_call_rate.numerator, r.vision_call_rate.denominator) == (2, 5)
    assert r.skipped_steps == {"quality_gate": 3, "vision": 3, "advisory": 2, "weather": 1}
    assert r.estimated_cost_saved_usd == pytest.approx(0.00006)


# ---------------------------------------------------------------- cost / latency / tiers
def test_tiers_and_step_stats():
    r1, r2 = run(cost=0.00002), run()
    models = [
        call(r1, "intent_router", latency=1), call(r1, "quality_gate", latency=30),
        call(r1, "vision", latency=20, cost=0.00002), call(r1, "advisory", latency=2),
        call(r2, "intent_router", latency=3), call(r2, "weather", latency=200, outcome="error"),
    ]
    c = m.cost_latency([r1, r2], models, WINDOW)
    tiers = {t.tier: t for t in c.by_tier}
    assert list(tiers) == ["small_model", "vision_model", "large_model", "tool"]
    assert (tiers["small_model"].calls, tiers["vision_model"].calls, tiers["large_model"].calls,
            tiers["tool"].calls) == (3, 1, 0, 2)
    assert tiers["small_model"].share_of_calls == 0.5 and tiers["vision_model"].share_of_cost == 1.0
    assert tiers["large_model"].share_of_calls == 0.0 and "none used yet" in tiers["large_model"].description
    steps = {s.step: s for s in c.by_step}
    assert steps["intent_router"].calls == 2 and steps["intent_router"].latency.avg_ms == 2
    assert steps["weather"].errors == 1 and steps["vision"].avg_cost_usd == pytest.approx(0.00002)


def test_what_if_baseline_adds_the_vision_cost_of_skipped_runs():
    runs = [run(cost=0.00002), run(cost=0.0, skipped=["vision"]), run(cost=0.0, skipped=["vision"])]
    c = m.cost_latency(runs, [], WINDOW)
    assert c.cost_total_usd == pytest.approx(0.00002)
    assert c.cost_if_vision_always_ran_usd == pytest.approx(0.00006)


def test_window_filter_in_the_store():
    store = InMemoryCaseStore()
    old, new = run(created=NOW - timedelta(days=10)), run(created=NOW - timedelta(hours=1))
    m1, m2 = call(old, "vision"), call(new, "vision")
    for r, md in ((old, m1), (new, m2)):
        store._runs.append(r)
        store._model_runs.append(md)
    assert len(store.list_runs()[0]) == 2
    runs, models = store.list_runs(NOW - timedelta(days=1))
    assert [r.id for r in runs] == [new.id] and [x.id for x in models] == [m2.id]


# ---------------------------------------------------------------- API: roles + real orchestrator data
SECRET = "test-secret-at-least-32-bytes-long!!"
FARMER, EXPERT = uuid4(), uuid4()


def headers(sub, app_metadata=None):
    claims = {"sub": str(sub), "aud": "authenticated", "exp": int(time.time()) + 600}
    if app_metadata:
        claims["app_metadata"] = app_metadata
    return {"Authorization": f"Bearer {jwt.encode(claims, SECRET, algorithm='HS256')}"}


FARMER_H, EXPERT_H = headers(FARMER), headers(EXPERT, {"role": "expert"})
ENDPOINTS = ["/api/metrics/overview", "/api/metrics/routes", "/api/metrics/cost-latency"]


@pytest.fixture
def client():
    store = InMemoryCaseStore()
    orch = Orchestrator(Settings(), vision=FakeVisionService(label=Category.RUST_LIKE, confidence=0.95))
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_orchestrator] = lambda: orch
    app.dependency_overrides[get_settings] = lambda: Settings(supabase_jwt_secret=SECRET)
    c = TestClient(app)
    c.store = store
    yield c
    app.dependency_overrides.clear()


def ask(c, text, image=None, conf=None):
    cid = c.post("/api/cases", json={"crop": "soybean", "symptom_context": text}, headers=FARMER_H).json()["id"]
    if image:
        c.post(f"/api/cases/{cid}/images", data={"kind": "leaf_closeup"},
               files={"file": ("x.jpg", image, "image/jpeg")}, headers=FARMER_H)
    return c.post(f"/api/cases/{cid}/analyze", headers=FARMER_H).json(), cid


@pytest.mark.parametrize("path", ENDPOINTS)
def test_metrics_need_the_expert_role(client, path):
    assert client.get(path).status_code == 401
    assert client.get(path, headers=FARMER_H).status_code == 403
    assert client.get(path, headers=headers(FARMER, {"role": "farmer"})).status_code == 403
    assert client.get(path, headers=EXPERT_H).status_code == 200


@pytest.mark.parametrize("path", ENDPOINTS)
def test_days_parameter_is_validated(client, path):
    assert client.get(path, params={"days": 0}, headers=EXPERT_H).status_code == 422
    assert client.get(path, params={"days": 366}, headers=EXPERT_H).status_code == 422
    assert client.get(path, params={"days": 7}, headers=EXPERT_H).status_code == 200


def test_endpoints_on_empty_database(client):
    o = client.get("/api/metrics/overview", headers=EXPERT_H).json()
    assert o["total_cases"] == 0 and o["escalation_rate"]["rate"] is None
    assert client.get("/api/metrics/routes", headers=EXPERT_H).json()["by_path"] == []


def test_metrics_match_what_the_orchestrator_actually_did(client):
    ask(client, "yellow spots on the leaves", GOOD_JPEG)        # image path, high confidence -> guidance
    ask(client, "Will it rain in my area?")                      # weather path
    ask(client, "Which pesticide and how much?")                 # treatment -> expert
    ask(client, "I want to talk to an expert")                   # expert request -> expert
    a, cid = ask(client, "yellow spots on the leaves")           # no photo -> quality gate fails
    assert a["state"] == "NEEDS_BETTER_IMAGE"
    client.post(f"/api/cases/{cid}/analyze", headers=FARMER_H)   # re-analysis: 6 analyses over 5 cases

    o = client.get("/api/metrics/overview", headers=EXPERT_H).json()
    assert (o["total_cases"], o["total_analyses"]) == (5, 6)
    assert o["decision_states"] == {"PRELIMINARY_GUIDANCE": 2, "EXPERT_REVIEW": 2, "NEEDS_BETTER_IMAGE": 2}
    assert o["escalation_rate"] == {"numerator": 2, "denominator": 6, "rate": pytest.approx(0.3333)}
    assert o["abstention_rate"]["numerator"] == 4
    assert o["cost_per_case_usd"] == pytest.approx(0.00002 / 5)
    # advisory ran for the image answer and for the treatment question (which has no verified source)
    assert (o["retrieval_success_rate"]["numerator"], o["retrieval_success_rate"]["denominator"]) == (1, 2)
    assert o["weather_sources"].get("demo", 0) + o["weather_sources"].get("live", 0) + \
        o["weather_sources"].get("cached", 0) >= 2  # weather path + high-confidence image path

    r = client.get("/api/metrics/routes", headers=EXPERT_H).json()
    paths = {p["path"]: p["count"] for p in r["by_path"]}
    assert paths == {"image_diagnosis": 3, "weather": 1, "treatment_safety": 1, "expert_escalation": 1}
    assert r["vision_call_rate"] == {"numerator": 1, "denominator": 6, "rate": pytest.approx(0.1667)}
    assert r["skipped_steps"]["vision"] == 5 and r["estimated_cost_saved_usd"] == pytest.approx(5 * 0.00002)

    c = client.get("/api/metrics/cost-latency", headers=EXPERT_H).json()
    tiers = {t["tier"]: t for t in c["by_tier"]}
    assert tiers["vision_model"]["calls"] == 1 and tiers["large_model"]["calls"] == 0
    assert tiers["small_model"]["calls"] == 6 + 3  # 6 intent_router + 3 quality_gate (three image-path analyses)
    assert c["cost_if_vision_always_ran_usd"] == pytest.approx(6 * 0.00002)
    assert c["latency_per_analysis"]["n"] == 6 and c["latency_per_analysis"]["p95_ms"] is not None
