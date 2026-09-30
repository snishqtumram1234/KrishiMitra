"""SupabaseCaseStore against a minimal in-process fake of PostgREST + Storage (httpx.MockTransport).

This checks request shapes and a full orchestrate_case round trip. It does not replace a test
against a real Supabase project (RLS, column types, bucket policies).
"""

import json
from datetime import UTC, datetime
from urllib.parse import parse_qsl, urlparse
from uuid import uuid4

import httpx
import pytest
from conftest import GOOD_JPEG

from app.config import Settings
from app.schemas.api import CaseCreate, ImageKind
from app.schemas.case import Category, DecisionState
from app.services.orchestrator import Orchestrator, orchestrate_case
from app.services.supabase_store import SupabaseCaseStore
from app.services.vision_service import FakeVisionService

URL, KEY = "https://proj.supabase.co", "service-role-key"


class FakeSupabase:
    def __init__(self):
        self.tables: dict[str, list[dict]] = {}
        self.objects: dict[str, tuple[bytes, str]] = {}
        self.requests: list[httpx.Request] = []

    def __call__(self, req: httpx.Request) -> httpx.Response:
        self.requests.append(req)
        assert req.headers["apikey"] == KEY and req.headers["authorization"] == f"Bearer {KEY}"
        path = urlparse(str(req.url)).path
        if path.startswith("/storage/v1/object/case-images/"):
            name = path.removeprefix("/storage/v1/object/case-images/")
            if req.method == "POST":
                assert req.headers.get("x-upsert") == "false"
                self.objects[name] = (req.content, req.headers["content-type"])
                return httpx.Response(200, json={"Key": f"case-images/{name}"})
            data, ctype = self.objects[name]
            return httpx.Response(200, content=data, headers={"content-type": ctype})

        table = path.removeprefix("/rest/v1/")
        rows = self.tables.setdefault(table, [])
        params = dict(parse_qsl(urlparse(str(req.url)).query))
        if req.method == "POST":
            new = json.loads(req.content)
            for r in new if isinstance(new, list) else [new]:
                r.setdefault("id", str(uuid4()))
                r.setdefault("created_at", datetime.now(UTC).isoformat())
                r.setdefault("decision_state", None)
                rows.append(r)
            return httpx.Response(201, json=new if isinstance(new, list) else [new])
        match = [r for r in rows if all(str(r.get(k)) == v.removeprefix("eq.")
                                        for k, v in params.items() if v.startswith("eq."))
                 and all(str(r.get(k)) in v.removeprefix("in.(").removesuffix(")").split(",")
                         for k, v in params.items() if v.startswith("in."))]
        if req.method == "PATCH":
            for r in match:
                r.update(json.loads(req.content))
            return httpx.Response(204)
        if "order" in params:
            col, direction = params["order"].split(".")
            match = sorted(match, key=lambda r: r[col], reverse=direction == "desc")
        if "limit" in params:
            match = match[: int(params["limit"])]
        return httpx.Response(200, json=match)


@pytest.fixture
def fake():
    return FakeSupabase()


@pytest.fixture
def store(fake):
    return SupabaseCaseStore(URL, KEY, client=httpx.Client(transport=httpx.MockTransport(fake)))


def test_requires_config():
    with pytest.raises(ValueError):
        SupabaseCaseStore("", "")


def test_create_get_list(store, fake):
    user = uuid4()
    case = store.create_case(user, CaseCreate(crop="soybean", symptom_context="spots"))
    assert case.user_id == user
    assert store.get_case(case.id) == case
    assert store.get_case(uuid4()) is None
    assert [c.id for c in store.list_cases(user)] == [case.id]
    assert store.list_cases(uuid4()) == []
    insert = next(r for r in fake.requests if r.method == "POST")
    assert insert.headers["prefer"] == "return=representation"


def test_image_goes_to_private_bucket_under_user_folder(store, fake):
    user = uuid4()
    case = store.create_case(user, CaseCreate(crop="soybean", symptom_context="spots"))
    meta = store.put_image(case, ImageKind.LEAF_CLOSEUP, "image/jpeg", GOOD_JPEG)
    assert meta.storage_path.startswith(f"{user}/{case.id}/leaf_closeup-") and meta.storage_path.endswith(".jpg")
    assert fake.objects[meta.storage_path] == (GOOD_JPEG, "image/jpeg")
    assert fake.tables["case_images"][0]["storage_path"] == meta.storage_path

    got = store.get_image(case.id, ImageKind.LEAF_CLOSEUP)
    assert got.data == GOOD_JPEG and got.meta.id == meta.id
    assert store.get_image(case.id, ImageKind.FIELD_OVERVIEW) is None


def test_orchestrate_case_round_trip(store, fake):
    user = uuid4()
    case = store.create_case(user, CaseCreate(crop="soybean", symptom_context="yellow spots on leaves"))
    store.put_image(case, ImageKind.LEAF_CLOSEUP, "image/jpeg", GOOD_JPEG)
    orch = Orchestrator(Settings(), vision=FakeVisionService(label=Category.RUST_LIKE, confidence=0.95))

    run, result = orchestrate_case(case.id, store, orch)

    assert len(fake.tables["routing_runs"]) == 1
    assert [m["step"] for m in fake.tables["model_runs"]] == run.details["steps"]
    assert store.get_case(case.id).decision_state == DecisionState.PRELIMINARY_GUIDANCE
    assert store.get_latest_run(case.id) == run
    got_run, models = store.get_run(run.id)
    assert got_run == run and len(models) == 5
    assert store.get_run(uuid4()) is None
    assert got_run.details["result"]["state"] == result.state.value


def test_expert_workflow_round_trip(store, fake):
    from app.schemas.expert import ExpertStatus, ReviewDecision, ReviewIn
    from app.services.expert_service import ExpertService

    user, expert = uuid4(), uuid4()
    case = store.create_case(user, CaseCreate(crop="soybean", symptom_context="yellow spots on leaves"))
    store.put_image(case, ImageKind.LEAF_CLOSEUP, "image/jpeg", GOOD_JPEG)
    store.put_image(case, ImageKind.FIELD_OVERVIEW, "image/jpeg", GOOD_JPEG)
    orch = Orchestrator(Settings(), vision=FakeVisionService(label=Category.RUST_LIKE, confidence=0.3))

    run, result = orchestrate_case(case.id, store, orch)
    assert result.state == DecisionState.EXPERT_REVIEW
    pending = store.list_expert_reviews(statuses={ExpertStatus.PENDING_REVIEW})
    assert len(pending) == 1 and pending[0].routing_run_id == run.id
    assert {i.kind for i in pending[0].snapshot.images} == {ImageKind.LEAF_CLOSEUP, ImageKind.FIELD_OVERVIEW}

    svc = ExpertService(store)
    svc.review(case.id, expert, ReviewIn(decision=ReviewDecision.REQUEST_MORE, notes="underside photo please"))
    assert store.list_expert_reviews(case.id)[0].status == ExpertStatus.AWAITING_FARMER
    svc.record_follow_up(case, user, "older leaves", None)
    assert store.list_expert_reviews(case.id)[0].status == ExpertStatus.FOLLOW_UP_RECEIVED
    assert [f.answer for f in store.list_follow_ups(case.id)] == ["older leaves"]
    assert [e.event_type for e in store.list_audit_events(case.id)] == [
        "escalation_created", "expert_review_submitted", "follow_up_submitted"]
    patch = [r for r in fake.requests if r.method == "PATCH" and "expert_reviews" in str(r.url)]
    assert patch and "created_at" not in json.loads(patch[0].content)

