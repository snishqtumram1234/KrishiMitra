import httpx
from fastapi.testclient import TestClient

from app.main import create_app


def test_database_failure_is_a_readable_502_with_cors_headers():
    app = create_app()

    @app.get("/boom")
    def boom():
        req = httpx.Request("POST", "https://x.supabase.co/rest/v1/crop_cases")
        raise httpx.HTTPStatusError(
            "bad", request=req, response=httpx.Response(401, json={"message": "Invalid API key", "code": "PGRST301"}, request=req)
        )

    r = TestClient(app, raise_server_exceptions=False).get("/boom")
    assert r.status_code == 502
    d = r.json()["detail"]
    assert d["upstream_status"] == 401 and d["upstream_message"] == "Invalid API key"
