"""CORS: browser frontends on allowed origins can call the API; nobody else gets CORS headers."""

import time
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.deps import get_store
from app.config import Settings, get_settings
from app.main import create_app
from app.services.case_store import InMemoryCaseStore

ALLOWED = "https://app.example.com"
LOCAL = "http://localhost:3000"
EVIL = "https://evil.example.net"
SECRET = "test-secret-at-least-32-bytes-long!!"


def make(origins=f"{ALLOWED},{LOCAL}", **kw) -> TestClient:
    settings = Settings(cors_allowed_origins=origins, supabase_jwt_secret=SECRET, **kw)
    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_store] = lambda: InMemoryCaseStore()
    return TestClient(app)


def bearer():
    tok = jwt.encode({"sub": str(uuid4()), "aud": "authenticated", "exp": int(time.time()) + 600}, SECRET,
                     algorithm="HS256")
    return {"Authorization": f"Bearer {tok}"}


def preflight(c, path, origin, method="POST", headers="authorization,content-type"):
    return c.options(path, headers={"Origin": origin, "Access-Control-Request-Method": method,
                                    "Access-Control-Request-Headers": headers})


# ---------------------------------------------------------------- preflight
@pytest.mark.parametrize("origin", [ALLOWED, LOCAL])
@pytest.mark.parametrize("path", ["/api/cases", "/api/cases/" + str(uuid4()) + "/images",
                                  "/api/cases/" + str(uuid4()) + "/analyze", "/api/weather",
                                  "/api/expert/cases", "/api/metrics/overview"])
def test_preflight_from_allowed_origin_succeeds_without_a_token(origin, path):
    """Browsers send OPTIONS with no Authorization header; it must not be rejected with 401."""
    r = preflight(make(), path, origin)
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == origin
    allowed = r.headers["access-control-allow-headers"].lower()
    assert "authorization" in allowed and "content-type" in allowed
    assert {"GET", "POST"} <= set(r.headers["access-control-allow-methods"].split(", "))
    assert r.headers["access-control-max-age"] == "600"


def test_preflight_from_unknown_origin_is_refused():
    r = preflight(make(), "/api/cases", EVIL)
    assert r.status_code == 400
    assert "access-control-allow-origin" not in r.headers


def test_unlisted_header_or_method_is_refused():
    c = make()
    assert preflight(c, "/api/cases", ALLOWED, headers="x-custom").status_code == 400
    assert preflight(c, "/api/cases", ALLOWED, method="DELETE").status_code == 400
    assert preflight(c, "/api/cases", ALLOWED, method="PUT").status_code == 400


# ---------------------------------------------------------------- real requests
def test_response_carries_cors_header_for_allowed_origin():
    r = make().get("/api/cases", headers={**bearer(), "Origin": ALLOWED})
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == ALLOWED
    assert "access-control-allow-credentials" not in r.headers  # Bearer token, not cookies


def test_error_responses_are_readable_by_the_browser_too():
    """Without CORS headers on 401/403/404/422 the frontend could not read the error message."""
    c = make()
    for headers, path, status in [({"Origin": ALLOWED}, "/api/cases", 401),
                                  ({**bearer(), "Origin": ALLOWED}, "/api/expert/cases", 403),
                                  ({**bearer(), "Origin": ALLOWED}, f"/api/cases/{uuid4()}", 404),
                                  ({**bearer(), "Origin": ALLOWED}, "/api/weather?district=Atlantis", 422)]:
        r = c.get(path, headers=headers)
        assert r.status_code == status
        assert r.headers["access-control-allow-origin"] == ALLOWED, path


def test_health_is_also_cors_enabled():
    r = make().get("/health", headers={"Origin": LOCAL})
    assert r.headers["access-control-allow-origin"] == LOCAL


def test_multipart_upload_request_passes_from_an_allowed_origin():
    c = make()
    cid = c.post("/api/cases", json={"crop": "soybean", "symptom_context": "x"},
                 headers={**bearer(), "Origin": ALLOWED})
    assert cid.status_code == 201 and cid.headers["access-control-allow-origin"] == ALLOWED


@pytest.mark.parametrize("origin", [EVIL, "http://localhost:3001", "https://app.example.com.evil.net",
                                    "http://app.example.com"])
def test_other_origins_get_no_cors_headers(origin):
    """The request itself still works (CORS is enforced by the browser), but it gets no allow header."""
    r = make().get("/api/cases", headers={**bearer(), "Origin": origin})
    assert "access-control-allow-origin" not in r.headers


def test_no_origin_header_means_no_cors_headers():
    r = make().get("/api/cases", headers=bearer())
    assert r.status_code == 200 and "access-control-allow-origin" not in r.headers


def test_no_wildcard_by_default():
    r = make().get("/health", headers={"Origin": ALLOWED})
    assert r.headers["access-control-allow-origin"] != "*"


# ---------------------------------------------------------------- configuration
def test_default_allows_the_local_nextjs_dev_server():
    assert Settings().cors_origins == ["http://localhost:3000", "http://127.0.0.1:3000"]


def test_empty_setting_disables_cors():
    c = make(origins="")
    r = c.get("/health", headers={"Origin": ALLOWED})
    assert r.status_code == 200 and "access-control-allow-origin" not in r.headers
    assert c.options("/api/cases", headers={"Origin": ALLOWED, "Access-Control-Request-Method": "POST"}
                     ).headers.get("access-control-allow-origin") is None


def test_whitespace_and_blanks_are_ignored():
    assert Settings(cors_allowed_origins=f" {ALLOWED} , ,{LOCAL},").cors_origins == [ALLOWED, LOCAL]


@pytest.mark.parametrize("bad", ["https://app.example.com/", "https://app.example.com/app", "app.example.com",
                                 "localhost:3000", "ftp://x.com", "https://a b.com", f"{ALLOWED},https://x.com/"])
def test_malformed_origins_fail_at_startup_with_a_clear_message(bad):
    with pytest.raises(ValidationError, match="Invalid CORS origin"):
        Settings(cors_allowed_origins=bad)


def test_wildcard_allowed_in_dev_but_never_in_production():
    assert Settings(cors_allowed_origins="*").cors_origins == ["*"]
    with pytest.raises(ValidationError, match="not allowed when ENVIRONMENT=production"):
        Settings(cors_allowed_origins="*", environment="production")


def test_production_accepts_explicit_https_origins():
    s = Settings(cors_allowed_origins="https://krishimitra.example.com", environment="production")
    assert s.cors_origins == ["https://krishimitra.example.com"]
    r = TestClient(create_app(s)).get("/health", headers={"Origin": "https://krishimitra.example.com"})
    assert r.headers["access-control-allow-origin"] == "https://krishimitra.example.com"
