from uuid import uuid4

from conftest import GOOD_JPEG
import pytest

from app.config import Settings
from app.schemas.api import CaseCreate, ImageKind
from app.schemas.case import Category, DecisionState
from app.services.advisory_service import AdvisoryService
from app.services.case_store import InMemoryCaseStore
from app.services.metrics_service import ESTIMATED_COST_USD
from app.services.orchestrator import CaseNotFound, Orchestrator, orchestrate_case
from app.services.vision_service import FakeVisionService

IMG = GOOD_JPEG


def setup(conf=0.95, label=Category.RUST_LIKE, image=IMG, **orch_kw):
    store = InMemoryCaseStore()
    case = store.create_case(CaseCreate(crop="soybean", symptom_context="yellow spots on leaves"))
    if image is not None:
        store.put_image(case.id, ImageKind.CLOSE_UP_LEAF, "image/jpeg", image)
    orch = Orchestrator(Settings(), vision=FakeVisionService(label=label, confidence=conf), **orch_kw)
    return store, case.id, orch


def test_unknown_case_raises():
    store, _, orch = setup()
    with pytest.raises(CaseNotFound):
        orchestrate_case(uuid4(), store, orch)


def test_persists_result_and_decision_state():
    store, cid, orch = setup()
    result = orchestrate_case(cid, store, orch)
    assert store.get_result(cid) == result
    assert store.get_case(cid).decision_state == DecisionState.PRELIMINARY_GUIDANCE


def test_one_routing_and_model_run_per_call_plus_decision_row():
    store, cid, orch = setup()
    result = orchestrate_case(cid, store, orch)
    routing, models = store.get_runs(cid)

    assert [r.route for r in routing] == [
        "quality_gate", "intent_router", "vision", "advisory", "weather", "policy_decision",
    ]
    assert len(models) == len(result.calls) == 5
    # every model_run points at its own routing step, in order
    for step, m in zip(routing, models):
        assert m.routing_run_id == step.id
        assert m.case_id == cid
    assert len({m.routing_run_id for m in models}) == len(models)

    final = routing[-1]
    assert final.decision_state == DecisionState.PRELIMINARY_GUIDANCE
    assert final.reason == "high_confidence"
    assert final.details["route_trace"][-1] == "decision:PRELIMINARY_GUIDANCE"
    assert all(r.decision_state is None for r in routing[:-1])


def test_latency_and_estimated_cost_are_logged():
    store, cid, orch = setup()
    result = orchestrate_case(cid, store, orch)
    routing, models = store.get_runs(cid)
    for r in routing[:-1]:
        assert r.latency_ms >= 0
        assert r.cost_usd == ESTIMATED_COST_USD[r.route]
    assert routing[-1].cost_usd == pytest.approx(sum(ESTIMATED_COST_USD[r.route] for r in routing[:-1]))
    assert routing[-1].cost_usd == pytest.approx(result.total_cost_usd)
    assert result.total_cost_usd > 0  # vision has a non-zero estimate


def test_vision_model_run_has_label_confidence_output():
    store, cid, orch = setup(conf=0.72, label=Category.LEAF_SPOT_LIKE)
    orchestrate_case(cid, store, orch)
    _, models = store.get_runs(cid)
    v = next(m for m in models if m.model_name == "fake-vision-random")
    assert v.predicted_label == "leaf_spot_like"
    assert v.confidence == pytest.approx(0.72)
    assert v.output[0]["label"] == "leaf_spot_like"


def test_intent_is_recorded_on_its_routing_row():
    store, cid, orch = setup()
    orchestrate_case(cid, store, orch)
    routing, _ = store.get_runs(cid)
    assert next(r for r in routing if r.route == "intent_router").intent == "diagnosis"


def test_failed_call_logs_error_and_escalates():
    class Boom(AdvisoryService):
        def retrieve(self, label, district):
            raise RuntimeError("advisory db down")

    store, cid, orch = setup(conf=0.72, advisory=Boom())
    result = orchestrate_case(cid, store, orch)
    routing, models = store.get_runs(cid)
    adv = next(m for m in models if m.model_name == "placeholder-advisory")
    assert adv.outcome == "error" and "advisory db down" in adv.error
    assert result.state == DecisionState.EXPERT_REVIEW
    assert routing[-1].decision_state == DecisionState.EXPERT_REVIEW


def test_early_stop_logs_only_steps_that_ran():
    store, cid, orch = setup(image=b"tiny")
    orchestrate_case(cid, store, orch)
    routing, models = store.get_runs(cid)
    assert [r.route for r in routing] == ["quality_gate", "policy_decision"]
    assert routing[-1].decision_state == DecisionState.NEEDS_BETTER_IMAGE
    assert len(models) == 1


def test_reanalysis_appends_rows_not_overwrites():
    store, cid, orch = setup()
    orchestrate_case(cid, store, orch)
    orchestrate_case(cid, store, orch)
    routing, models = store.get_runs(cid)
    assert sum(r.route == "policy_decision" for r in routing) == 2
    assert len(models) == 10
