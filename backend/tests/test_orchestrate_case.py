from uuid import uuid4

import pytest
from conftest import GOOD_JPEG

from app.config import Settings
from app.schemas.api import CaseCreate, ImageKind
from app.schemas.case import Category, DecisionState
from app.services.advisory_service import AdvisoryService
from app.services.case_store import InMemoryCaseStore
from app.services.metrics_service import ESTIMATED_COST_USD
from app.services.orchestrator import CaseNotFound, Orchestrator, orchestrate_case
from app.services.vision_service import FakeVisionService

USER = uuid4()


def setup(conf=0.95, label=Category.RUST_LIKE, image=GOOD_JPEG, **orch_kw):
    store = InMemoryCaseStore()
    case = store.create_case(USER, CaseCreate(crop="soybean", symptom_context="yellow spots on leaves"))
    if image is not None:
        store.put_image(case, ImageKind.LEAF_CLOSEUP, "image/jpeg", image)
    orch = Orchestrator(Settings(), vision=FakeVisionService(label=label, confidence=conf), **orch_kw)
    return store, case.id, orch


def test_unknown_case_raises():
    store, _, orch = setup()
    with pytest.raises(CaseNotFound):
        orchestrate_case(uuid4(), store, orch)


def test_one_routing_run_per_analysis_with_linked_model_runs():
    store, cid, orch = setup()
    run, result = orchestrate_case(cid, store, orch)
    stored, models = store.get_run(run.id)

    assert stored == run
    assert run.route == "image_diagnosis"
    assert run.details["steps"] == ["intent_router", "quality_gate", "vision", "advisory", "weather"]
    assert run.decision_state == DecisionState.PRELIMINARY_GUIDANCE == result.state
    assert run.reason == "high_confidence" and run.intent == "crop_health_image" and run.outcome == "ok"
    assert [m.step for m in sorted(models, key=lambda m: m.created_at)] == run.details["steps"]
    assert all(m.routing_run_id == run.id and m.case_id == cid for m in models)
    assert store.get_case(cid).decision_state == DecisionState.PRELIMINARY_GUIDANCE


def test_full_result_is_recoverable_from_the_run():
    store, cid, orch = setup()
    run, result = orchestrate_case(cid, store, orch)
    assert run.details["result"] == result.model_dump(mode="json")


def test_latency_and_estimated_cost():
    store, cid, orch = setup()
    run, result = orchestrate_case(cid, store, orch)
    _, models = store.get_run(run.id)
    for m in models:
        assert m.latency_ms >= 0 and m.cost_usd == ESTIMATED_COST_USD[m.step]
    assert run.cost_usd == pytest.approx(sum(m.cost_usd for m in models)) == pytest.approx(result.total_cost_usd)
    assert run.latency_ms == sum(m.latency_ms for m in models)
    assert run.cost_usd > 0


def test_vision_model_run_has_label_confidence_output():
    store, cid, orch = setup(conf=0.72, label=Category.LEAF_SPOT_LIKE)
    run, _ = orchestrate_case(cid, store, orch)
    _, models = store.get_run(run.id)
    v = next(m for m in models if m.step == "vision")
    assert v.predicted_label == "leaf_spot_like"
    assert v.confidence == pytest.approx(0.72)
    assert v.output[0]["label"] == "leaf_spot_like"


def test_failed_call_logs_error_and_marks_run_degraded():
    class Boom(AdvisoryService):
        def retrieve(self, label, district):
            raise RuntimeError("advisory db down")

    store, cid, orch = setup(conf=0.72, advisory=Boom())
    run, result = orchestrate_case(cid, store, orch)
    _, models = store.get_run(run.id)
    adv = next(m for m in models if m.step == "advisory")
    assert adv.outcome == "error" and "advisory db down" in adv.error
    assert run.outcome == "degraded"
    assert result.state == run.decision_state == DecisionState.EXPERT_REVIEW


def test_early_stop_logs_only_steps_that_ran():
    store, cid, orch = setup(image=b"tiny")
    run, _ = orchestrate_case(cid, store, orch)
    _, models = store.get_run(run.id)
    assert run.details["steps"] == ["intent_router", "quality_gate"]
    assert run.decision_state == DecisionState.NEEDS_BETTER_IMAGE
    assert len(models) == 2


def test_reanalysis_adds_a_new_run_and_keeps_the_old_one():
    store, cid, orch = setup()
    first, _ = orchestrate_case(cid, store, orch)
    second, _ = orchestrate_case(cid, store, orch)
    assert first.id != second.id
    assert store.get_latest_run(cid).id == second.id
    assert store.get_run(first.id) is not None


def test_latest_image_of_a_kind_is_used():
    store, cid, orch = setup(image=b"tiny")
    store.put_image(store.get_case(cid), ImageKind.LEAF_CLOSEUP, "image/jpeg", GOOD_JPEG)
    run, _ = orchestrate_case(cid, store, orch)
    assert run.decision_state == DecisionState.PRELIMINARY_GUIDANCE
