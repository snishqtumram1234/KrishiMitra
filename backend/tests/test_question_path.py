"""The no-photo "ask a question" path (POST /api/questions) and the rule that a photo is required
only for the crop-health route."""

import time
import uuid

import jwt
import pytest
from conftest import GOOD_JPEG
from fastapi.testclient import TestClient

from app.api.deps import get_orchestrator, get_store
from app.config import Settings, get_settings
from app.main import app
from app.schemas.case import Category
from app.services.case_store import InMemoryCaseStore
from app.services.orchestrator import Orchestrator
from app.services.vision_service import FakeVisionService
from app.services.weather_service import MemoryWeatherSnapshots, WeatherService

SECRET = "test-secret-at-least-32-bytes-long!!"


def headers(sub=None):
    tok = jwt.encode({"sub": str(sub or uuid.uuid4()), "aud": "authenticated", "exp": int(time.time()) + 600},
                     SECRET, algorithm="HS256")
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture
def api():
    store = InMemoryCaseStore()
    weather = WeatherService(Settings(weather_live_enabled=False), snapshots=MemoryWeatherSnapshots())
    orch = Orchestrator(Settings(allow_demo_sources=True),
                        vision=FakeVisionService(label=Category.RUST_LIKE, confidence=0.95), weather=weather)
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_orchestrator] = lambda: orch
    app.dependency_overrides[get_settings] = lambda: Settings(supabase_jwt_secret=SECRET)
    c = TestClient(app)
    c.h = headers()
    c.store = store
    yield c
    app.dependency_overrides.clear()


def ask(c, question, **kw):
    return c.post("/api/questions", json={"question": question, **kw}, headers=c.h)


# ---------------------------------------------------------------- questions answered with no photo
@pytest.mark.parametrize("question,path,state", [
    ("Will it rain in my area?", "weather", "PRELIMINARY_GUIDANCE"),
    ("What is the weather forecast for this week?", "weather", "PRELIMINARY_GUIDANCE"),
    ("उद्या पाऊस पडेल का?", "weather", "PRELIMINARY_GUIDANCE"),
    ("Show me the latest KVK advisory for soybean", "advisory_lookup", "PRELIMINARY_GUIDANCE"),
    ("सोयाबीनसाठी कृषी विज्ञान केंद्राचा सल्ला सांगा", "advisory_lookup", "PRELIMINARY_GUIDANCE"),
    ("When should I sow soybean?", "general_crop_question", "PRELIMINARY_GUIDANCE"),
    ("Which pesticide and how much?", "treatment_safety", "EXPERT_REVIEW"),
    ("कोणते कीटकनाशक फवारावे?", "treatment_safety", "EXPERT_REVIEW"),
    ("I want to talk to an expert", "expert_escalation", "EXPERT_REVIEW"),
    ("मला तज्ञांशी बोलायचे आहे", "expert_escalation", "EXPERT_REVIEW"),
    ("My cotton leaves have spots", "unsupported_request", "UNSUPPORTED"),
])
def test_text_questions_are_answered_without_any_photo(api, question, path, state):
    r = ask(api, question)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["state"] == state and body["result"]["path"] == path
    calls = [c["route"] for c in body["result"]["calls"]]
    assert "quality_gate" not in calls and "vision" not in calls  # no image step is ever involved
    assert "close_up_photo" not in body["missing_information"]


def test_question_creates_a_case_marked_as_a_question_and_it_is_listed(api):
    body = ask(api, "Will it rain in my area?", district="Pune", language="mr").json()
    case = api.get(f"/api/cases/{body['case_id']}", headers=api.h).json()
    assert case["entry_point"] == "question" and case["language"] == "mr" and case["district"] == "Pune"
    assert case["symptom_context"] == "Will it rain in my area?" and case["crop"] == "soybean"
    assert case["images"] == [] and case["decision_state"] == "PRELIMINARY_GUIDANCE"
    assert [c["id"] for c in api.get("/api/cases", headers=api.h).json()] == [body["case_id"]]


def test_the_district_reaches_the_weather_lookup(api):
    body = ask(api, "Will it rain in my area?", district="Latur").json()
    weather = next(c for c in body["result"]["calls"] if c["route"] == "weather")
    assert weather["output"]["district"] == "Latur"


def test_an_unclear_question_asks_for_a_description(api):
    body = ask(api, "hello").json()
    assert body["state"] == "NEEDS_MORE_CONTEXT" and body["reason_code"] == "intent_unclear"
    assert body["follow_up_options"] == {"question_id": "describe_problem", "answer_type": "text", "options": []}
    assert body["missing_information"] == ["symptom_description"]


def test_a_followup_can_turn_an_unclear_question_into_an_answer(api):
    case_id = ask(api, "hello").json()["case_id"]
    r = api.post(f"/api/cases/{case_id}/follow-up", data={"question_id": "describe_problem", "answer": "Will it rain tomorrow?"},
                 headers=api.h)
    assert r.json()["result"]["path"] == "weather"


# ---------------------------------------------------------------- the photo is required only for crop health
def test_a_crop_health_question_without_a_photo_asks_for_one_and_can_be_resumed(api):
    body = ask(api, "Yellow spots on the leaves").json()
    assert body["state"] == "NEEDS_BETTER_IMAGE" and body["result"]["path"] == "image_diagnosis"
    assert (body["reason_code"], body["reason_detail"]) == ("quality_failed", "missing_image")
    assert body["missing_information"] == ["close_up_photo"]
    assert [c["route"] for c in body["result"]["calls"]] == ["intent_router", "quality_gate"]
    qg = body["result"]["calls"][1]["output"]
    assert qg["next_action"] == "upload_image" and qg["issues"] == ["missing_image"]

    case_id = body["case_id"]  # upload to the same case and analyse again
    assert api.post(f"/api/cases/{case_id}/images", data={"kind": "leaf_closeup"},
                    files={"file": ("leaf.jpg", GOOD_JPEG, "image/jpeg")}, headers=api.h).status_code == 201
    again = api.post(f"/api/cases/{case_id}/analyze", headers=api.h).json()
    assert again["state"] == "PRELIMINARY_GUIDANCE" and again["result"]["path"] == "image_diagnosis"
    assert api.get(f"/api/cases/{case_id}", headers=api.h).json()["entry_point"] == "question"


@pytest.mark.parametrize("text,needs_photo", [
    ("Yellow spots on the leaves", True),
    ("Caterpillars are eating holes in the leaves", True),
    ("पानांवर पिवळे डाग आले आहेत", True),
    ("Will it rain in my area?", False),
    ("Show me the KVK advisory", False),
    ("When should I sow soybean?", False),
    ("Which pesticide and how much?", False),
    ("I want to talk to an expert", False),
    ("My cotton leaves have spots", False),
])
def test_only_the_crop_health_route_needs_a_photo(api, text, needs_photo):
    """Same rule on the photo form (POST /api/cases) and the question path: no photo is sent."""
    via_case = api.post("/api/cases", json={"crop": "soybean", "symptom_context": text}, headers=api.h).json()["id"]
    via_form = api.post(f"/api/cases/{via_case}/analyze", headers=api.h).json()
    via_question = ask(api, text).json()
    for body in (via_form, via_question):
        asks_for_photo = body["state"] == "NEEDS_BETTER_IMAGE" and body["missing_information"] == ["close_up_photo"]
        assert asks_for_photo is needs_photo, (text, body["state"], body["missing_information"])
    assert via_form["result"]["path"] == via_question["result"]["path"]


def test_a_photo_does_not_force_a_text_question_down_the_image_route(api):
    """With a photo attached, a weather question is still a weather question."""
    cid = api.post("/api/cases", json={"crop": "soybean", "symptom_context": "Will it rain in my area?"}, headers=api.h).json()["id"]
    api.post(f"/api/cases/{cid}/images", data={"kind": "leaf_closeup"}, files={"file": ("x.jpg", GOOD_JPEG, "image/jpeg")},
             headers=api.h)
    body = api.post(f"/api/cases/{cid}/analyze", headers=api.h).json()
    assert body["result"]["path"] == "weather"
    assert "vision" in body["result"]["skipped_steps"]


# ---------------------------------------------------------------- validation, auth, ownership
@pytest.mark.parametrize("payload", [{}, {"question": ""}, {"question": "x" * 2001}, {"question": "ok", "language": "fr"}])
def test_question_validation(api, payload):
    assert api.post("/api/questions", json=payload, headers=api.h).status_code == 422
    assert api.get("/api/cases", headers=api.h).json() == []  # a rejected question creates nothing


def test_question_needs_a_token(api):
    assert api.post("/api/questions", json={"question": "Will it rain?"}).status_code == 401
    bad = {"Authorization": "Bearer nope"}
    assert api.post("/api/questions", json={"question": "Will it rain?"}, headers=bad).status_code == 401


def test_a_question_case_belongs_to_its_asker(api):
    case_id = ask(api, "Will it rain in my area?").json()["case_id"]
    other = headers()
    assert api.get(f"/api/cases/{case_id}", headers=other).status_code == 404
    assert api.get(f"/api/cases/{case_id}/analysis", headers=other).status_code == 404
    assert api.get("/api/cases", headers=other).json() == []


def test_the_question_endpoint_takes_json_not_files(api):
    r = api.post("/api/questions", data={"question": "x"}, files={"file": ("a.jpg", GOOD_JPEG, "image/jpeg")}, headers=api.h)
    assert r.status_code == 422
    assert r.json()["detail"][0]["input"] == "<binary data omitted>"  # readable error, not a 500


def test_multipart_sent_to_any_json_endpoint_is_a_422_not_a_crash(api):
    files = {"file": ("a.jpg", GOOD_JPEG, "image/jpeg")}
    for path in ("/api/cases", "/api/questions"):
        assert api.post(path, data={"crop": "soybean"}, files=files, headers=api.h).status_code == 422
    expert = {"Authorization": "Bearer " + jwt.encode({"sub": str(uuid.uuid4()), "aud": "authenticated",
              "app_metadata": {"role": "expert"}, "exp": int(time.time()) + 600}, SECRET, algorithm="HS256")}
    assert api.post(f"/api/expert/cases/{uuid.uuid4()}/review", data={"x": "1"}, files=files, headers=expert).status_code == 422


def test_ordinary_validation_errors_keep_their_shape(api):
    r = api.post("/api/cases", json={"crop": "cotton", "symptom_context": "x"}, headers=api.h)
    assert r.status_code == 422
    e = r.json()["detail"][0]
    assert e["loc"] == ["body", "crop"] and "Only soybean" in e["msg"] and e["input"] == "cotton"


def test_question_escalations_open_expert_cases_like_any_other(api):
    expert = {"Authorization": "Bearer " + jwt.encode(
        {"sub": str(uuid.uuid4()), "aud": "authenticated", "app_metadata": {"role": "expert"},
         "exp": int(time.time()) + 600}, SECRET, algorithm="HS256")}
    case_id = ask(api, "I want to talk to an expert").json()["case_id"]
    row = api.get("/api/expert/cases", headers=expert).json()[0]
    assert row["case_id"] == case_id and row["escalation_reason_code"] == "farmer_requested_expert"
    assert row["image_ids"] == []
