import time
from datetime import date, timedelta
from uuid import uuid4

import cv2
import jwt
import pytest
from conftest import GOOD_JPEG, encode, leaf_photo
from fastapi.testclient import TestClient

from app.api.deps import get_orchestrator, get_store
from app.config import Settings, get_settings
from app.main import app
from app.schemas.case import Category
from app.services.case_store import InMemoryCaseStore
from app.services.orchestrator import Orchestrator
from app.services.vision_service import FakeVisionService

SECRET = "test-secret-at-least-32-bytes-long!!"
ALICE, BOB = uuid4(), uuid4()
CASE = {"crop": "soybean", "district": "Pune", "symptom_context": "yellow spots on leaves"}


def token(sub=ALICE, secret=SECRET, aud="authenticated", exp_in=3600) -> str:
    return jwt.encode({"sub": str(sub), "aud": aud, "role": "authenticated", "exp": int(time.time()) + exp_in},
                      secret, algorithm="HS256")


def auth(sub=ALICE) -> dict:
    return {"Authorization": f"Bearer {token(sub)}"}


@pytest.fixture
def make_client():
    def _make(confidence: float = 0.95, label: Category = Category.RUST_LIKE) -> TestClient:
        store = InMemoryCaseStore()
        orch = Orchestrator(Settings(), vision=FakeVisionService(label=label, confidence=confidence))
        app.dependency_overrides[get_store] = lambda: store
        app.dependency_overrides[get_orchestrator] = lambda: orch
        app.dependency_overrides[get_settings] = lambda: Settings(supabase_jwt_secret=SECRET)
        return TestClient(app)

    yield _make
    app.dependency_overrides.clear()


def new_case(c, who=ALICE, **kw) -> str:
    r = c.post("/api/cases", json={**CASE, **kw}, headers=auth(who))
    assert r.status_code == 201, r.text
    return r.json()["id"]


def upload(c, cid, kind="leaf_closeup", data=GOOD_JPEG, who=ALICE, fname="leaf.jpg", ctype="image/jpeg"):
    return c.post(f"/api/cases/{cid}/images", data={"kind": kind},
                  files={"file": (fname, data, ctype)}, headers=auth(who))


# ---------------------------------------------------------------- create / read
def test_create_and_get_case(make_client):
    c = make_client()
    r = c.post("/api/cases", json={**CASE, "growth_stage": "R3", "recent_rainfall": "heavy last week",
                                   "symptom_started_at": "2026-09-20", "language": "mr"}, headers=auth())
    assert r.status_code == 201
    body = r.json()
    assert body["user_id"] == str(ALICE) and body["decision_state"] is None
    assert body["symptom_started_at"] == "2026-09-20" and body["language"] == "mr"
    assert c.get(f"/api/cases/{body['id']}", headers=auth()).json()["growth_stage"] == "R3"


@pytest.mark.parametrize("crop", ["Soybean", " SOYBEAN "])
def test_soybean_is_normalised(make_client, crop):
    c = make_client()
    r = c.post("/api/cases", json={**CASE, "crop": crop}, headers=auth())
    assert r.json()["crop"] == "soybean"


@pytest.mark.parametrize("patch", [
    {"crop": "cotton"},
    {"crop": ""},
    {"symptom_context": ""},
    {"language": "fr"},
    {"symptom_started_at": str(date.today() + timedelta(days=2))},
])
def test_create_validation(make_client, patch):
    c = make_client()
    r = c.post("/api/cases", json={**CASE, **patch}, headers=auth())
    assert r.status_code == 422


def test_non_soybean_error_says_why(make_client):
    c = make_client()
    r = c.post("/api/cases", json={**CASE, "crop": "cotton"}, headers=auth())
    assert "Only soybean" in r.text


def test_list_only_returns_my_cases_newest_first(make_client):
    c = make_client()
    a1, a2 = new_case(c), new_case(c)
    new_case(c, who=BOB)
    ids = [x["id"] for x in c.get("/api/cases", headers=auth()).json()]
    assert ids == [a2, a1]
    assert len(c.get("/api/cases", headers=auth(BOB)).json()) == 1


def test_other_users_case_is_404(make_client):
    c = make_client()
    cid = new_case(c, who=BOB)
    assert c.get(f"/api/cases/{cid}", headers=auth()).status_code == 404
    assert upload(c, cid).status_code == 404
    assert c.post(f"/api/cases/{cid}/analyze", headers=auth()).status_code == 404
    assert c.get(f"/api/cases/{cid}/analysis", headers=auth()).status_code == 404


def test_unknown_case_is_404(make_client):
    c = make_client()
    missing = uuid4()
    for method, path in [("get", ""), ("post", "/analyze"), ("get", "/analysis")]:
        assert getattr(c, method)(f"/api/cases/{missing}{path}", headers=auth()).status_code == 404


# ---------------------------------------------------------------- auth
@pytest.mark.parametrize("method,path", [
    ("post", "/api/cases"), ("get", "/api/cases"), ("get", f"/api/cases/{uuid4()}"),
    ("post", f"/api/cases/{uuid4()}/images"), ("post", f"/api/cases/{uuid4()}/analyze"),
    ("get", f"/api/cases/{uuid4()}/analysis"), ("get", f"/api/runs/{uuid4()}"),
])
def test_every_route_requires_a_token(make_client, method, path):
    c = make_client()
    assert getattr(c, method)(path).status_code == 401


@pytest.mark.parametrize("bad", [
    lambda: token(secret="wrong-secret-also-32-bytes-long!!!!"),
    lambda: token(aud="anon"),
    lambda: token(exp_in=-10),
    lambda: "not.a.jwt",
    lambda: jwt.encode({"aud": "authenticated", "exp": int(time.time()) + 60}, SECRET, algorithm="HS256"),
    lambda: jwt.encode({"sub": "not-a-uuid", "aud": "authenticated", "exp": int(time.time()) + 60},
                       SECRET, algorithm="HS256"),
])
def test_bad_tokens_are_rejected(make_client, bad):
    c = make_client()
    r = c.get("/api/cases", headers={"Authorization": f"Bearer {bad()}"})
    assert r.status_code == 401


def test_health_stays_public(make_client):
    assert make_client().get("/health").status_code == 200


def test_auth_not_configured_fails_closed():
    app.dependency_overrides[get_settings] = lambda: Settings(supabase_jwt_secret="", supabase_url="")
    try:
        r = TestClient(app).get("/api/cases", headers=auth())
        assert r.status_code == 503
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------- upload
def test_upload_returns_metadata_with_private_storage_path(make_client):
    c = make_client()
    cid = new_case(c)
    r = upload(c, cid)
    assert r.status_code == 201
    body = r.json()
    assert body["kind"] == "leaf_closeup" and body["size_bytes"] == len(GOOD_JPEG)
    assert body["content_type"] == "image/jpeg"
    assert body["storage_path"].startswith(f"{ALICE}/{cid}/leaf_closeup-")


def test_content_type_comes_from_bytes_not_client(make_client):
    c = make_client()
    cid = new_case(c)
    png = encode(leaf_photo(), ".png")
    r = upload(c, cid, data=png, fname="leaf.jpg", ctype="image/jpeg")
    assert r.json()["content_type"] == "image/png"


@pytest.mark.parametrize("data,kind,code", [
    (b"%PDF-1.4 not an image", "leaf_closeup", 415),
    (encode(leaf_photo(), ".bmp"), "leaf_closeup", 415),
    (b"", "leaf_closeup", 400),
    (b"x" * (10 * 1024 * 1024 + 1), "leaf_closeup", 413),
    (GOOD_JPEG, "selfie", 422),
], ids=["pdf", "bmp", "empty", "over_10mb", "bad_kind"])
def test_upload_validation(make_client, data, kind, code):
    c = make_client()
    cid = new_case(c)
    assert upload(c, cid, data=data, kind=kind).status_code == code


# ---------------------------------------------------------------- analyze / analysis / runs
def test_full_flow(make_client):
    c = make_client(confidence=0.95)
    cid = new_case(c)
    assert c.get(f"/api/cases/{cid}/analysis", headers=auth()).status_code == 404
    upload(c, cid)

    r = c.post(f"/api/cases/{cid}/analyze", headers=auth())
    assert r.status_code == 200
    a = r.json()
    assert a["state"] == "PRELIMINARY_GUIDANCE" and a["case_id"] == cid
    assert a["result"]["preliminary_label"] == "rust_like"
    assert "not a confirmed diagnosis" in a["result"]["message"]

    assert c.get(f"/api/cases/{cid}/analysis", headers=auth()).json() == a
    assert c.get(f"/api/cases/{cid}", headers=auth()).json()["decision_state"] == "PRELIMINARY_GUIDANCE"

    trace = c.get(f"/api/runs/{a['routing_run_id']}", headers=auth()).json()
    assert [s["step"] for s in trace["steps"]] == ["quality_gate", "intent_router", "vision", "advisory", "weather"]
    assert trace["route_trace"][-1] == "decision:PRELIMINARY_GUIDANCE"
    assert trace["decision_state"] == "PRELIMINARY_GUIDANCE"
    vision = next(s for s in trace["steps"] if s["step"] == "vision")
    assert vision["predicted_label"] == "rust_like" and vision["cost_usd"] > 0
    assert trace["total_cost_usd"] == pytest.approx(sum(s["cost_usd"] for s in trace["steps"]))
    assert trace["total_latency_ms"] >= 0


def test_other_users_run_is_404(make_client):
    c = make_client()
    cid = new_case(c)
    upload(c, cid)
    run_id = c.post(f"/api/cases/{cid}/analyze", headers=auth()).json()["routing_run_id"]
    assert c.get(f"/api/runs/{run_id}", headers=auth(BOB)).status_code == 404
    assert c.get(f"/api/runs/{uuid4()}", headers=auth()).status_code == 404


def test_analysis_returns_latest_run(make_client):
    c = make_client()
    cid = new_case(c)
    first = c.post(f"/api/cases/{cid}/analyze", headers=auth()).json()  # no image yet
    assert first["state"] == "NEEDS_BETTER_IMAGE"
    upload(c, cid)
    second = c.post(f"/api/cases/{cid}/analyze", headers=auth()).json()
    assert second["state"] == "PRELIMINARY_GUIDANCE"
    assert second["routing_run_id"] != first["routing_run_id"]
    assert c.get(f"/api/cases/{cid}/analysis", headers=auth()).json()["routing_run_id"] == second["routing_run_id"]
    # the old run is still retrievable
    assert c.get(f"/api/runs/{first['routing_run_id']}", headers=auth()).status_code == 200


def test_blurry_upload_is_accepted_but_analysis_asks_for_better_image(make_client):
    c = make_client()
    cid = new_case(c)
    assert upload(c, cid, data=encode(cv2.GaussianBlur(leaf_photo(), (31, 31), 0))).status_code == 201
    a = c.post(f"/api/cases/{cid}/analyze", headers=auth()).json()
    assert a["state"] == "NEEDS_BETTER_IMAGE"
    assert a["result"]["reason"] == "quality:blurry"


def test_low_confidence_uses_field_overview(make_client):
    c = make_client(confidence=0.3)
    cid = new_case(c)
    upload(c, cid)
    assert c.post(f"/api/cases/{cid}/analyze", headers=auth()).json()["state"] == "NEEDS_MORE_CONTEXT"
    upload(c, cid, kind="field_overview")
    assert c.post(f"/api/cases/{cid}/analyze", headers=auth()).json()["state"] == "EXPERT_REVIEW"
