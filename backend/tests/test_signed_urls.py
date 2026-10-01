"""GET /api/cases/{case_id}/images/{image_id}/signed-url: 5-minute links, only for the case owner and experts
(on escalated cases). Plus image ids in case and expert responses."""

import time
import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

import httpx
import jwt
import pytest
from conftest import GOOD_JPEG, encode, leaf_photo
from fastapi.testclient import TestClient

from app.api.deps import get_orchestrator, get_store
from app.config import Settings, get_settings
from app.main import app
from app.schemas.api import CaseCreate, ImageKind
from app.schemas.case import Category
from app.services import signed_urls
from app.services.case_store import InMemoryCaseStore
from app.services.orchestrator import Orchestrator
from app.services.supabase_store import SupabaseCaseStore
from app.services.vision_service import FakeVisionService
from app.services.weather_service import MemoryWeatherSnapshots, WeatherService

SECRET = "test-secret-at-least-32-bytes-long!!"
FARMER, OTHER, EXPERT = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()


def token(sub, role=None):
    claims = {"sub": str(sub), "aud": "authenticated", "exp": int(time.time()) + 600}
    if role:
        claims["app_metadata"] = {"role": role}
    return {"Authorization": "Bearer " + jwt.encode(claims, SECRET, algorithm="HS256")}


FARMER_H, OTHER_H, EXPERT_H = token(FARMER), token(OTHER), token(EXPERT, "expert")
PNG = encode(leaf_photo(), ".png")


@pytest.fixture
def api():
    store = InMemoryCaseStore(signing_secret="s" * 32)
    weather = WeatherService(Settings(weather_live_enabled=False), snapshots=MemoryWeatherSnapshots())
    orch = Orchestrator(Settings(allow_demo_sources=True), vision=FakeVisionService(label=Category.RUST_LIKE, confidence=0.3),
                        weather=weather)
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_orchestrator] = lambda: orch
    app.dependency_overrides[get_settings] = lambda: Settings(supabase_jwt_secret=SECRET)
    c = TestClient(app)
    c.store = store
    yield c
    app.dependency_overrides.clear()


def case_with_photo(c, who=FARMER_H, data=GOOD_JPEG, ctype="image/jpeg", text="yellow spots on leaves"):
    cid = c.post("/api/cases", json={"crop": "soybean", "symptom_context": text}, headers=who).json()["id"]
    img = c.post(f"/api/cases/{cid}/images", data={"kind": "leaf_closeup"}, files={"file": ("x", data, ctype)}, headers=who).json()
    return cid, img["id"]


def escalate(c, cid, who=FARMER_H):
    """Low confidence + a field photo already present -> expert review."""
    c.post(f"/api/cases/{cid}/images", data={"kind": "field_overview"}, files={"file": ("f.jpg", GOOD_JPEG, "image/jpeg")}, headers=who)
    assert c.post(f"/api/cases/{cid}/analyze", headers=who).json()["state"] == "EXPERT_REVIEW"


def url(cid, iid):
    return f"/api/cases/{cid}/images/{iid}/signed-url"


# ---------------------------------------------------------------- who may get a link
def test_the_owner_gets_a_five_minute_link(api):
    cid, iid = case_with_photo(api)
    before = datetime.now(UTC)
    r = api.get(url(cid, iid), headers=FARMER_H)
    assert r.status_code == 200, r.text
    body = r.json()
    assert (body["image_id"], body["case_id"], body["kind"], body["content_type"]) == (iid, cid, "leaf_closeup", "image/jpeg")
    assert body["expires_in"] == 300
    exp = datetime.fromisoformat(body["expires_at"])
    assert timedelta(seconds=295) <= exp - before <= timedelta(seconds=305)
    assert body["url"].startswith("http") and "/api/files/" in body["url"]


def test_the_link_really_serves_the_photo_without_any_auth_header(api):
    cid, iid = case_with_photo(api, data=PNG, ctype="image/png")
    link = api.get(url(cid, iid), headers=FARMER_H).json()["url"]
    got = api.get(urlparse(link).path)  # no Authorization header: the token in the URL is the credential
    assert got.status_code == 200 and got.content == PNG and got.headers["content-type"] == "image/png"
    assert got.headers["cache-control"] == "private, no-store" and got.headers["x-content-type-options"] == "nosniff"


def test_another_farmer_gets_404_exactly_like_a_missing_image(api):
    cid, iid = case_with_photo(api)
    assert api.get(url(cid, iid), headers=OTHER_H).status_code == 404
    assert api.get(url(cid, uuid.uuid4()), headers=FARMER_H).status_code == 404
    assert api.get(url(uuid.uuid4(), iid), headers=FARMER_H).status_code == 404
    assert api.get(url(cid, iid), headers=OTHER_H).json() == api.get(url(cid, uuid.uuid4()), headers=FARMER_H).json()


def test_no_token_is_401(api):
    cid, iid = case_with_photo(api)
    assert api.get(url(cid, iid)).status_code == 401
    assert api.get(url(cid, iid), headers={"Authorization": "Bearer nope"}).status_code == 401


def test_the_image_must_belong_to_the_case_in_the_url(api):
    cid_a, img_a = case_with_photo(api)
    cid_b, _ = case_with_photo(api)
    assert api.get(url(cid_b, img_a), headers=FARMER_H).status_code == 404  # right owner, wrong case


def test_an_expert_gets_a_link_for_an_escalated_case(api):
    cid, iid = case_with_photo(api)
    escalate(api, cid)
    r = api.get(url(cid, iid), headers=EXPERT_H)
    assert r.status_code == 200 and r.json()["expires_in"] == 300
    assert api.get(urlparse(r.json()["url"]).path).content == GOOD_JPEG


def test_an_expert_cannot_get_links_for_cases_that_were_never_escalated(api):
    cid, iid = case_with_photo(api)
    assert api.get(url(cid, iid), headers=EXPERT_H).status_code == 404


def test_a_farmer_who_claims_expert_in_user_metadata_gets_nothing(api):
    cid, iid = case_with_photo(api)
    escalate(api, cid)
    spoof = {"Authorization": "Bearer " + jwt.encode({"sub": str(OTHER), "aud": "authenticated", "user_metadata": {"role": "expert"},
                                                     "exp": int(time.time()) + 600}, SECRET, algorithm="HS256")}
    assert api.get(url(cid, iid), headers=spoof).status_code == 404


def test_expert_access_is_audited_owner_access_is_not(api):
    cid, iid = case_with_photo(api)
    escalate(api, cid)
    api.get(url(cid, iid), headers=FARMER_H)
    assert [e.event_type for e in api.store.list_audit_events(uuid.UUID(cid))] == ["escalation_created"]
    api.get(url(cid, iid), headers=EXPERT_H)
    ev = api.store.list_audit_events(uuid.UUID(cid))[-1]
    assert (ev.event_type, ev.actor_id, ev.actor_role) == ("image_signed_url_issued", EXPERT, "expert")
    assert ev.details["image_id"] == iid and ev.details["image_kind"] == "leaf_closeup"
    api.get(url(cid, uuid.uuid4()), headers=EXPERT_H)  # a refused request leaves no event
    assert len(api.store.list_audit_events(uuid.UUID(cid))) == 2


# ---------------------------------------------------------------- the link itself: expiry and tampering
def test_links_expire_after_five_minutes():
    img = uuid.uuid4()
    token_, expires = signed_urls.sign(img, "k" * 32, now=1_000_000)
    assert expires == 1_000_300
    assert signed_urls.verify(token_, "k" * 32, now=1_000_299) == img
    assert signed_urls.verify(token_, "k" * 32, now=1_000_300) is None
    assert signed_urls.verify(token_, "k" * 32, now=1_000_301) is None


def test_expired_and_tampered_links_are_refused_by_the_route(api):
    cid, iid = case_with_photo(api)
    secret = api.store._signing_secret
    expired, _ = signed_urls.sign(uuid.UUID(iid), secret, ttl=-1)
    assert api.get(f"/api/files/{expired}").status_code == 404
    good, _ = signed_urls.sign(uuid.UUID(iid), secret)
    assert api.get(f"/api/files/{good}").status_code == 200
    img_id, exp, sig = good.split(".")
    for bad in (f"{img_id}.{int(exp) + 3600}.{sig}",  # extended expiry
                f"{uuid.uuid4()}.{exp}.{sig}",  # swapped image
                f"{img_id}.{exp}.{sig[:-1]}0", f"{img_id}.{exp}", "garbage", f"{img_id}.x.{sig}"):
        assert api.get(f"/api/files/{bad}").status_code == 404, bad
    other_secret, _ = signed_urls.sign(uuid.UUID(iid), "z" * 32)
    assert api.get(f"/api/files/{other_secret}").status_code == 404  # signed with a different key


def test_each_request_issues_a_fresh_link(api):
    cid, iid = case_with_photo(api)
    a = api.get(url(cid, iid), headers=FARMER_H).json()
    time.sleep(1.1)
    b = api.get(url(cid, iid), headers=FARMER_H).json()
    assert a["url"] != b["url"]


def test_the_files_route_does_not_serve_with_the_supabase_store():
    from app.api.files import serve_signed_file
    from fastapi import HTTPException

    class NoLookup:  # a store without image_for_signed_token (like SupabaseCaseStore)
        pass

    with pytest.raises(HTTPException) as e:
        serve_signed_file("a.b.c", NoLookup())
    assert e.value.status_code == 404


# ---------------------------------------------------------------- image ids in case and expert responses
def test_case_responses_include_every_photo_with_its_id(api):
    cid, first = case_with_photo(api)
    second = api.post(f"/api/cases/{cid}/images", data={"kind": "field_overview"},
                      files={"file": ("f.jpg", GOOD_JPEG, "image/jpeg")}, headers=FARMER_H).json()["id"]
    newer = api.post(f"/api/cases/{cid}/images", data={"kind": "leaf_closeup"},
                     files={"file": ("n.jpg", GOOD_JPEG, "image/jpeg")}, headers=FARMER_H).json()["id"]
    one = api.get(f"/api/cases/{cid}", headers=FARMER_H).json()
    assert [i["id"] for i in one["images"]] == [first, second, newer]  # oldest first; the newest of a kind is analysed
    assert {i["kind"] for i in one["images"]} == {"leaf_closeup", "field_overview"}
    assert all(i["case_id"] == cid and i["storage_path"] for i in one["images"])
    listed = api.get("/api/cases", headers=FARMER_H).json()
    assert [i["id"] for i in listed[0]["images"]] == [first, second, newer]
    assert api.post("/api/cases", json={"crop": "soybean", "symptom_context": "x"}, headers=FARMER_H).json()["images"] == []


def test_a_case_list_only_shows_each_cases_own_photos(api):
    c1, i1 = case_with_photo(api)
    c2, i2 = case_with_photo(api)
    by = {c["id"]: [i["id"] for i in c["images"]] for c in api.get("/api/cases", headers=FARMER_H).json()}
    assert by == {c1: [i1], c2: [i2]}


def test_every_image_id_in_a_case_can_be_turned_into_a_link(api):
    cid, _ = case_with_photo(api)
    for img in api.get(f"/api/cases/{cid}", headers=FARMER_H).json()["images"]:
        assert api.get(url(cid, img["id"]), headers=FARMER_H).status_code == 200


def test_expert_responses_include_image_ids(api):
    cid, iid = case_with_photo(api)
    escalate(api, cid)
    row = api.get("/api/expert/cases", headers=EXPERT_H).json()[0]
    snap = api.get(f"/api/expert/cases/{cid}", headers=EXPERT_H).json()["current"]["snapshot"]
    assert iid in row["image_ids"] and len(row["image_ids"]) == 2
    assert {i["id"] for i in snap["images"]} == set(row["image_ids"])
    for image_id in row["image_ids"]:  # the expert can open every photo the case lists
        assert api.get(url(cid, image_id), headers=EXPERT_H).status_code == 200


# ---------------------------------------------------------------- Supabase signing (against a fake Storage API)
def test_supabase_store_asks_storage_to_sign_with_a_five_minute_expiry():
    seen = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen["url"], seen["body"], seen["auth"] = str(req.url), req.content, req.headers["authorization"]
        return httpx.Response(200, json={"signedURL": "/object/sign/case-images/u/c/leaf.jpg?token=abc"})

    store = SupabaseCaseStore("https://proj.supabase.co", "service-key", client=httpx.Client(transport=httpx.MockTransport(handler)))
    from app.schemas.api import ImageOut

    img = ImageOut(id=uuid.uuid4(), case_id=uuid.uuid4(), kind=ImageKind.LEAF_CLOSEUP, storage_path="u/c/leaf.jpg",
                   content_type="image/jpeg", size_bytes=1, created_at=datetime.now(UTC))
    link = store.signed_image_url(img, 300)
    assert seen["url"] == "https://proj.supabase.co/storage/v1/object/sign/case-images/u/c/leaf.jpg"
    assert seen["body"] == b'{"expiresIn":300}' and seen["auth"] == "Bearer service-key"
    assert link == "https://proj.supabase.co/storage/v1/object/sign/case-images/u/c/leaf.jpg?token=abc"


def test_supabase_store_image_lookups_and_case_entry_point():
    rows = {"case_images": [], "crop_cases": []}

    def handler(req: httpx.Request) -> httpx.Response:
        path = urlparse(str(req.url)).path.removeprefix("/rest/v1/")
        q = dict(httpx.QueryParams(req.url.query))
        if req.method == "POST":
            import json as _json
            row = _json.loads(req.content)
            row.setdefault("id", str(uuid.uuid4()))
            row.setdefault("created_at", datetime.now(UTC).isoformat())
            row.setdefault("decision_state", None)
            rows[path].append(row)
            return httpx.Response(201, json=[row])
        out = rows[path]
        for k, v in q.items():
            if v.startswith("eq."):
                out = [r for r in out if str(r.get(k)) == v[3:]]
            if v.startswith("in."):
                out = [r for r in out if str(r.get(k)) in v[4:-1].split(",")]
        return httpx.Response(200, json=out)

    store = SupabaseCaseStore("https://proj.supabase.co", "k", client=httpx.Client(transport=httpx.MockTransport(handler)))
    user = uuid.uuid4()
    case = store.create_case(user, CaseCreate(crop="soybean", symptom_context="Will it rain?"), entry_point="question")
    assert case.entry_point == "question" and rows["crop_cases"][0]["entry_point"] == "question"
    assert store.get_case(case.id).entry_point == "question"
    assert store.get_image_meta(uuid.uuid4()) is None
    img_id = uuid.uuid4()
    rows["case_images"].append({"id": str(img_id), "case_id": str(case.id), "kind": "leaf_closeup", "storage_path": "p",
                                "content_type": "image/jpeg", "size_bytes": 3, "created_at": datetime.now(UTC).isoformat()})
    assert store.get_image_meta(img_id).case_id == case.id
    batch = store.list_images_for_cases([case.id, uuid.uuid4()])
    assert [i.id for i in batch[case.id]] == [img_id]
