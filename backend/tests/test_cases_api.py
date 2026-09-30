from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_orchestrator, get_store
from app.config import Settings
from app.main import app
from app.schemas.case import Category
from app.services.case_store import InMemoryCaseStore
from app.services.orchestrator import Orchestrator
from app.services.vision_service import FakeVisionService

IMG = b"x" * 2048
CASE = {"crop": "soybean", "district": "Pune", "symptom_context": "yellow spots on leaves"}


@pytest.fixture
def make_client():
    def _make(confidence: float = 0.95, label: Category = Category.RUST_LIKE) -> TestClient:
        store = InMemoryCaseStore()
        orch = Orchestrator(Settings(), vision=FakeVisionService(label=label, confidence=confidence))
        app.dependency_overrides[get_store] = lambda: store
        app.dependency_overrides[get_orchestrator] = lambda: orch
        return TestClient(app)

    yield _make
    app.dependency_overrides.clear()


def upload(client, case_id, kind="close_up_leaf", data=IMG, ctype="image/jpeg"):
    return client.post(
        f"/cases/{case_id}/images", params={"kind": kind}, files={"file": ("leaf.jpg", data, ctype)}
    )


def test_create_and_get_case(make_client):
    c = make_client()
    r = c.post("/cases", json=CASE)
    assert r.status_code == 201
    body = r.json()
    assert body["decision_state"] is None and body["language"] == "en"
    assert c.get(f"/cases/{body['id']}").json()["crop"] == "soybean"


def test_create_case_validation(make_client):
    c = make_client()
    assert c.post("/cases", json={"crop": "soybean"}).status_code == 422
    assert c.post("/cases", json={**CASE, "language": "fr"}).status_code == 422
    assert c.post("/cases", json={**CASE, "crop": ""}).status_code == 422


def test_unknown_case_404(make_client):
    c = make_client()
    missing = uuid4()
    assert c.get(f"/cases/{missing}").status_code == 404
    assert upload(c, missing).status_code == 404
    assert c.post(f"/cases/{missing}/analyze").status_code == 404
    assert c.get(f"/cases/{missing}/result").status_code == 404


def test_upload_validation(make_client):
    c = make_client()
    cid = c.post("/cases", json=CASE).json()["id"]
    assert upload(c, cid).status_code == 201
    assert upload(c, cid, ctype="application/pdf").status_code == 415
    assert upload(c, cid, data=b"").status_code == 400
    assert upload(c, cid, kind="selfie").status_code == 422
    assert upload(c, cid, data=b"x" * (10 * 1024 * 1024 + 1)).status_code == 413


def test_full_flow_high_confidence(make_client):
    c = make_client(confidence=0.95)
    cid = c.post("/cases", json=CASE).json()["id"]
    assert c.get(f"/cases/{cid}/result").status_code == 404  # not analyzed yet
    img = upload(c, cid).json()
    assert img["size_bytes"] == 2048 and img["kind"] == "close_up_leaf"

    r = c.post(f"/cases/{cid}/analyze")
    assert r.status_code == 200
    body = r.json()
    assert body["state"] == "PRELIMINARY_GUIDANCE"
    assert body["preliminary_label"] == "rust_like"
    assert [x["route"] for x in body["calls"]] == [
        "quality_gate", "intent_router", "vision", "advisory", "weather",
    ]
    assert c.get(f"/cases/{cid}").json()["decision_state"] == "PRELIMINARY_GUIDANCE"
    assert c.get(f"/cases/{cid}/result").json() == body


def test_analyze_without_image_needs_better_image(make_client):
    c = make_client()
    cid = c.post("/cases", json=CASE).json()["id"]
    assert c.post(f"/cases/{cid}/analyze").json()["state"] == "NEEDS_BETTER_IMAGE"


def test_reupload_then_reanalyze_after_poor_image(make_client):
    c = make_client()
    cid = c.post("/cases", json=CASE).json()["id"]
    upload(c, cid, data=b"tiny")
    assert c.post(f"/cases/{cid}/analyze").json()["state"] == "NEEDS_BETTER_IMAGE"
    upload(c, cid)  # replaces the poor image
    assert c.post(f"/cases/{cid}/analyze").json()["state"] == "PRELIMINARY_GUIDANCE"


def test_low_confidence_uses_field_overview(make_client):
    c = make_client(confidence=0.3)
    cid = c.post("/cases", json=CASE).json()["id"]
    upload(c, cid)
    assert c.post(f"/cases/{cid}/analyze").json()["state"] == "NEEDS_MORE_CONTEXT"
    upload(c, cid, kind="field_overview")
    assert c.post(f"/cases/{cid}/analyze").json()["state"] == "EXPERT_REVIEW"


def test_non_soybean_unsupported(make_client):
    c = make_client()
    cid = c.post("/cases", json={**CASE, "crop": "cotton"}).json()["id"]
    upload(c, cid)
    assert c.post(f"/cases/{cid}/analyze").json()["state"] == "UNSUPPORTED"
