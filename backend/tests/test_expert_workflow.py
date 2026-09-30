"""Expert escalation, review, follow-up, audit trail, and role restrictions."""

import time
from uuid import UUID, uuid4

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
FARMER, OTHER_FARMER, EXPERT = uuid4(), uuid4(), uuid4()


def token(sub, app_metadata=None, user_metadata=None) -> dict:
    claims = {"sub": str(sub), "aud": "authenticated", "role": "authenticated", "exp": int(time.time()) + 600}
    if app_metadata is not None:
        claims["app_metadata"] = app_metadata
    if user_metadata is not None:
        claims["user_metadata"] = user_metadata
    return {"Authorization": f"Bearer {jwt.encode(claims, SECRET, algorithm='HS256')}"}


FARMER_H = token(FARMER)
EXPERT_H = token(EXPERT, app_metadata={"role": "expert"})


class Env:
    def __init__(self, confidence=0.3):
        self.store = InMemoryCaseStore()
        self.vision = FakeVisionService(label=Category.RUST_LIKE, confidence=confidence)
        orch = Orchestrator(Settings(), vision=self.vision)
        app.dependency_overrides[get_store] = lambda: self.store
        app.dependency_overrides[get_orchestrator] = lambda: orch
        app.dependency_overrides[get_settings] = lambda: Settings(supabase_jwt_secret=SECRET)
        self.c = TestClient(app)

    def case(self, text="yellow spots on leaves", headers=FARMER_H, **kw) -> str:
        r = self.c.post("/api/cases", json={"crop": "soybean", "symptom_context": text, **kw}, headers=headers)
        assert r.status_code == 201, r.text
        return r.json()["id"]

    def upload(self, cid, kind="leaf_closeup", data=GOOD_JPEG):
        return self.c.post(f"/api/cases/{cid}/images", data={"kind": kind},
                           files={"file": ("x.jpg", data, "image/jpeg")}, headers=FARMER_H)

    def analyze(self, cid):
        return self.c.post(f"/api/cases/{cid}/analyze", headers=FARMER_H).json()

    def escalated(self, text="yellow spots on leaves"):
        """A case the policy sends to EXPERT_REVIEW: low confidence with a field photo already present."""
        cid = self.case(text)
        self.upload(cid)
        self.upload(cid, "field_overview")
        a = self.analyze(cid)
        assert a["state"] == "EXPERT_REVIEW", a
        return cid

    def review(self, cid, headers=EXPERT_H, **body):
        return self.c.post(f"/api/expert/cases/{cid}/review", json=body, headers=headers)

    def events(self, cid):
        return [e.event_type for e in self.store.list_audit_events(UUID(cid))]


@pytest.fixture
def env():
    e = Env()
    yield e
    app.dependency_overrides.clear()


# ---------------------------------------------------------------- role restrictions
EXPERT_ROUTES = [
    ("get", "/api/expert/cases", None),
    ("get", "/api/expert/cases/{cid}", None),
    ("post", "/api/expert/cases/{cid}/review", {"decision": "unknown", "notes": "x"}),
]


@pytest.mark.parametrize("method,path,body", EXPERT_ROUTES, ids=["list", "detail", "review"])
def test_expert_routes_need_a_token(env, method, path, body):
    cid = env.escalated()
    r = getattr(env.c, method)(path.format(cid=cid), **({"json": body} if body else {}))
    assert r.status_code == 401


@pytest.mark.parametrize("method,path,body", EXPERT_ROUTES, ids=["list", "detail", "review"])
@pytest.mark.parametrize("who", [
    token(FARMER),                                                  # the case owner
    token(OTHER_FARMER),                                            # another farmer
    token(FARMER, user_metadata={"role": "expert"}),                # self-assigned role: user_metadata is user-editable
    token(FARMER, app_metadata={"role": "farmer"}),
    token(FARMER, app_metadata={"role": "Expert "}),                # no fuzzy matching
    token(FARMER, app_metadata="expert"),                           # malformed claim
], ids=["owner", "other_farmer", "user_metadata_spoof", "farmer_role", "near_miss", "malformed"])
def test_non_experts_are_forbidden(env, method, path, body, who):
    cid = env.escalated()
    r = getattr(env.c, method)(path.format(cid=cid), headers=who, **({"json": body} if body else {}))
    assert r.status_code == 403
    assert "expert_review_submitted" not in env.events(cid)


@pytest.mark.parametrize("method,path,body", EXPERT_ROUTES, ids=["list", "detail", "review"])
def test_experts_are_allowed(env, method, path, body):
    cid = env.escalated()
    r = getattr(env.c, method)(path.format(cid=cid), headers=EXPERT_H, **({"json": body} if body else {}))
    assert r.status_code == 200, r.text


def test_expert_role_does_not_grant_access_to_farmer_cases(env):
    cid = env.escalated()
    assert env.c.get(f"/api/cases/{cid}", headers=EXPERT_H).status_code == 404
    assert env.c.post(f"/api/cases/{cid}/follow-up", data={"answer": "x"}, headers=EXPERT_H).status_code == 404


# ---------------------------------------------------------------- escalation
def test_escalation_creates_pending_expert_case_with_evidence(env):
    cid = env.escalated()
    detail = env.c.get(f"/api/expert/cases/{cid}", headers=EXPERT_H).json()
    cur = detail["current"]
    assert cur["status"] == "pending_review" and cur["escalation_reason"] == "low_confidence_escalate"
    snap = cur["snapshot"]
    assert {i["kind"] for i in snap["images"]} == {"leaf_closeup", "field_overview"}
    vision = next(p for p in snap["predictions"] if p["step"] == "vision")
    assert vision["label"] == "rust_like" and vision["confidence"] == pytest.approx(0.3)
    assert "clearer or additional close-up photos of affected leaves" in snap["missing_information"]
    assert {"growth stage", "when the symptoms started", "recent rainfall"} <= set(snap["missing_information"])
    assert snap["question"] == "yellow spots on leaves"
    assert env.events(cid) == ["escalation_created"]


def test_escalation_includes_retrieved_sources_and_known_fields(env):
    env.vision._confidence = 0.95
    cid = env.case(growth_stage="R3", recent_rainfall="heavy")
    env.upload(cid)

    class NoWeather:  # high confidence needs weather; make it unavailable to force escalation
        model_name = "none"

        def get(self, district):
            from app.schemas.orchestration import WeatherResult
            return WeatherResult(available=False, district=district)

    orch = Orchestrator(Settings(), vision=env.vision, weather=NoWeather())
    app.dependency_overrides[get_orchestrator] = lambda: orch
    assert env.analyze(cid)["state"] == "EXPERT_REVIEW"
    snap = env.c.get(f"/api/expert/cases/{cid}", headers=EXPERT_H).json()["current"]["snapshot"]
    assert snap["sources"] and snap["sources"][0]["verified"]
    assert "current weather for the district" in snap["missing_information"]
    assert "growth stage" not in snap["missing_information"] and "recent rainfall" not in snap["missing_information"]


def test_treatment_and_expert_requests_escalate_without_images(env):
    for text, reason in [("Which pesticide and how much?", "treatment_needs_expert"),
                         ("I want to talk to an expert", "farmer_requested_expert")]:
        cid = env.case(text)
        assert env.analyze(cid)["state"] == "EXPERT_REVIEW"
        cur = env.c.get(f"/api/expert/cases/{cid}", headers=EXPERT_H).json()["current"]
        assert cur["escalation_reason"] == reason and cur["snapshot"]["images"] == []


def test_non_escalated_cases_do_not_create_expert_cases(env):
    env.vision._confidence = 0.95
    cid = env.case()
    env.upload(cid)
    assert env.analyze(cid)["state"] == "PRELIMINARY_GUIDANCE"
    assert env.c.get(f"/api/expert/cases/{cid}", headers=EXPERT_H).status_code == 404
    assert env.events(cid) == []


def test_re_analysis_refreshes_the_pending_case_instead_of_duplicating(env):
    cid = env.escalated()
    env.analyze(cid)
    detail = env.c.get(f"/api/expert/cases/{cid}", headers=EXPERT_H).json()
    assert len(detail["history"]) == 1
    assert env.events(cid) == ["escalation_created", "escalation_updated"]


def test_queue_lists_pending_by_default(env):
    a, b = env.escalated(), env.escalated()
    env.review(a, decision="unknown", notes="cannot tell")
    pending = env.c.get("/api/expert/cases", headers=EXPERT_H).json()
    assert [p["case_id"] for p in pending] == [b]
    everything = env.c.get("/api/expert/cases", params={"status": "all"}, headers=EXPERT_H).json()
    assert {p["case_id"] for p in everything} == {a, b}
    assert env.c.get("/api/expert/cases", params={"status": "bogus"}, headers=EXPERT_H).status_code == 422


# ---------------------------------------------------------------- review
@pytest.mark.parametrize("body,status", [
    ({"decision": "likely", "label": "rust_like", "notes": "Pustules on underside, typical rust"}, "reviewed"),
    ({"decision": "insufficient", "notes": "Photo too far"}, "reviewed"),
    ({"decision": "unknown", "notes": ""}, "reviewed"),
    ({"decision": "request_more", "notes": "Send a photo of the leaf underside"}, "awaiting_farmer"),
])
def test_review_decisions(env, body, status):
    cid = env.escalated()
    r = env.review(cid, **body)
    assert r.status_code == 200, r.text
    rec = r.json()
    assert rec["status"] == status and rec["decision"] == body["decision"]
    assert rec["reviewer_id"] == str(EXPERT) and rec["reviewed_at"]
    assert env.events(cid) == ["escalation_created", "expert_review_submitted"]
    ev = env.store.list_audit_events()[-1]
    assert ev.actor_id == EXPERT and ev.actor_role == "expert" and ev.details["decision"] == body["decision"]


@pytest.mark.parametrize("body", [
    {"decision": "likely"},                                          # likely needs a label
    {"decision": "insufficient", "label": "rust_like"},              # label only with likely
    {"decision": "request_more", "notes": "  "},                     # must say what to send
    {"decision": "confirmed", "notes": "x"},                         # not a decision
    {"decision": "likely", "label": "cancer"},
])
def test_review_validation(env, body):
    cid = env.escalated()
    assert env.review(cid, **body).status_code == 422
    assert env.events(cid) == ["escalation_created"]


def test_review_with_recommended_advisory(env):
    cid = env.escalated()
    adv = {"title": "Soybean rust management", "publisher": "ICAR-IISR Indore", "url": "https://example.org/a"}
    rec = env.review(cid, decision="likely", label="rust_like", notes="ok", recommended_advisory=adv).json()
    assert rec["recommended_advisory"] == adv


def test_cannot_review_twice_or_unescalated_cases(env):
    cid = env.escalated()
    assert env.review(cid, decision="unknown").status_code == 200
    assert env.review(cid, decision="unknown").status_code == 409
    assert env.review(str(uuid4()), decision="unknown").status_code == 404


def test_farmer_sees_the_review(env):
    cid = env.escalated()
    env.review(cid, decision="likely", label="rust_like", notes="Looks like rust")
    a = env.c.get(f"/api/cases/{cid}/analysis", headers=FARMER_H).json()
    assert a["expert"]["status"] == "reviewed" and a["expert"]["label"] == "rust_like"
    assert a["expert"]["notes"] == "Looks like rust"


# ---------------------------------------------------------------- follow-up loop
def test_request_more_then_follow_up_reruns_and_reescalates(env):
    cid = env.escalated()
    env.review(cid, decision="request_more", notes="Which leaves are affected: old or new?")
    a = env.c.get(f"/api/cases/{cid}/analysis", headers=FARMER_H).json()
    assert a["expert"]["status"] == "awaiting_farmer"
    assert a["expert"]["notes"] == "Which leaves are affected: old or new?"

    r = env.c.post(f"/api/cases/{cid}/follow-up", data={"answer": "Mostly the older lower leaves"}, headers=FARMER_H)
    assert r.status_code == 200, r.text
    assert r.json()["state"] == "EXPERT_REVIEW"  # still low confidence -> a fresh escalation

    detail = env.c.get(f"/api/expert/cases/{cid}", headers=EXPERT_H).json()
    assert [h["status"] for h in detail["history"]] == ["pending_review", "follow_up_received"]
    assert detail["current"]["snapshot"]["follow_ups"] == ["Mostly the older lower leaves"]
    assert env.events(cid) == ["escalation_created", "expert_review_submitted", "follow_up_submitted",
                               "escalation_created"]
    fu = next(e for e in env.store.list_audit_events() if e.event_type == "follow_up_submitted")
    assert fu.actor_id == FARMER and fu.actor_role == "farmer" and fu.details["answered_expert_requests"]


def test_follow_up_answer_reaches_the_orchestrator(env):
    cid = env.case("hello")  # unclear, no photo -> NEEDS_MORE_CONTEXT
    assert env.analyze(cid)["state"] == "NEEDS_MORE_CONTEXT"
    r = env.c.post(f"/api/cases/{cid}/follow-up", data={"answer": "Will it rain tomorrow?"}, headers=FARMER_H)
    assert r.json()["result"]["intent"] == "weather_context"


def test_follow_up_with_better_image_resolves_the_case(env):
    env.vision._confidence = 0.95
    cid = env.case()
    env.upload(cid, data=encode(cv2.GaussianBlur(leaf_photo(), (31, 31), 0)))
    assert env.analyze(cid)["state"] == "NEEDS_BETTER_IMAGE"
    r = env.c.post(f"/api/cases/{cid}/follow-up", data={"kind": "leaf_closeup"},
                   files={"file": ("sharp.jpg", GOOD_JPEG, "image/jpeg")}, headers=FARMER_H)
    assert r.status_code == 200 and r.json()["state"] == "PRELIMINARY_GUIDANCE"
    fu = env.store.list_follow_ups(UUID(cid))
    assert len(fu) == 1 and fu[0].image_id is not None and fu[0].answer is None


def test_follow_up_validation_and_ownership(env):
    cid = env.escalated()
    assert env.c.post(f"/api/cases/{cid}/follow-up", data={"answer": "  "}, headers=FARMER_H).status_code == 422
    assert env.c.post(f"/api/cases/{cid}/follow-up", files={"file": ("x.pdf", b"%PDF-1.4", "application/pdf")},
                      headers=FARMER_H).status_code == 415
    assert env.c.post(f"/api/cases/{cid}/follow-up", data={"answer": "x"},
                      headers=token(OTHER_FARMER)).status_code == 404
    assert env.c.post(f"/api/cases/{cid}/follow-up", data={"answer": "x"}).status_code == 401
    assert "follow_up_submitted" not in env.events(cid)
