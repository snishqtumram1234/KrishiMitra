import json
import socket
import threading
import time
from datetime import UTC, datetime, timedelta

import httpx
import jwt
import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_weather_service
from app.config import Settings, get_settings
from app.main import app
from app.schemas.case import CaseInput, DecisionState
from app.services.orchestrator import Orchestrator
from app.services.policy_engine import PolicyEngine
from app.services.weather_service import MemoryWeatherSnapshots, WeatherService

NOW = datetime(2026, 10, 1, 4, 45, tzinfo=UTC)  # 10:15 IST
LIVE = Settings(weather_live_enabled=True)


def open_meteo_payload(temp=23.0, hour="2026-10-01T10:00"):
    """Same shape as the real Open-Meteo response (checked against the live API)."""
    hours = [f"2026-10-01T{h:02d}:00" for h in range(24)] + [f"2026-10-02T{h:02d}:00" for h in range(24)]
    precip = [0.0] * 48
    precip[9] = 5.0    # 09:00 today: before the current hour, must NOT count
    precip[10] = 1.0   # 10:00 today: counts
    precip[33] = 2.5   # 09:00 tomorrow: inside 24 h, counts
    precip[34] = 7.0   # 10:00 tomorrow: exactly 24 h later, must NOT count
    return {
        "latitude": 18.52, "longitude": 73.87, "timezone": "Asia/Kolkata", "utc_offset_seconds": 19800,
        "current": {"time": hour, "interval": 900, "temperature_2m": temp, "relative_humidity_2m": 91,
                    "precipitation": 0.2, "wind_speed_10m": 6.5},
        "hourly": {"time": hours, "precipitation": precip},
        "daily": {"time": ["2026-10-01", "2026-10-02"], "precipitation_probability_max": [71, 43]},
    }


class FakeOpenMeteo:
    def __init__(self):
        self.mode = "ok"
        self.requests: list[httpx.Request] = []

    def __call__(self, req: httpx.Request) -> httpx.Response:
        self.requests.append(req)
        if self.mode == "ok":
            return httpx.Response(200, json=open_meteo_payload())
        if self.mode == "500":
            return httpx.Response(500, text="upstream error")
        if self.mode == "timeout":
            raise httpx.ReadTimeout("timed out", request=req)
        if self.mode == "garbage":
            return httpx.Response(200, text="<html>maintenance</html>")
        if self.mode == "missing_fields":
            return httpx.Response(200, json={"utc_offset_seconds": 19800})
        raise AssertionError(self.mode)


@pytest.fixture
def api():
    return FakeOpenMeteo()


def make(api, settings=LIVE, clock=lambda: NOW, snapshots=None, **kw):
    return WeatherService(settings, snapshots=snapshots or MemoryWeatherSnapshots(),
                          client=httpx.Client(transport=httpx.MockTransport(api)), clock=clock, **kw)


def assert_honest(r, district="Pune"):
    """Every result: source, district, and observed_at (unless nothing was available). Never IMD."""
    assert r.source in {"live", "cached", "demo", "unavailable"}
    assert r.district == district
    if r.available:
        assert r.observed_at is not None and r.observed_at.tzinfo is not None
    assert "imd" not in json.dumps(r.model_dump(mode="json")).lower()


# ---------------------------------------------------------------- live
def test_live_success(api):
    svc = make(api)
    r = svc.get("Pune")
    assert_honest(r)
    assert r.source == "live" and r.provider == "Open-Meteo" and r.error is None and r.usable
    assert r.observed_at == datetime.fromisoformat("2026-10-01T10:00:00+05:30")
    assert r.temperature_c == 23.0 and r.humidity_pct == 91 and r.rain_probability_max_pct == 71
    assert r.rain_next_24h_mm == 3.5  # 10:00 today .. 09:00 tomorrow only
    assert "Open-Meteo" in r.source_label and "live" in r.source_label
    q = dict(api.requests[0].url.params)
    assert (q["latitude"], q["longitude"], q["timezone"]) == ("18.52", "73.86", "Asia/Kolkata")


def test_a_failed_snapshot_save_still_returns_the_live_weather(api):
    """The snapshot is a cache. A database error while saving it must not turn good weather into 'unavailable'."""
    class BrokenStore(MemoryWeatherSnapshots):
        def save_weather_snapshot(self, snap):
            raise httpx.HTTPStatusError("insert failed", request=httpx.Request("POST", "https://x"),
                                        response=httpx.Response(400))

    r = make(api, snapshots=BrokenStore()).get("Pune")
    assert r.source == "live" and r.usable


def test_every_result_is_stored_with_its_source(api):
    store = MemoryWeatherSnapshots()
    svc = make(api, snapshots=store)
    svc.get("Pune")
    api.mode = "500"
    svc.get("Pune")
    assert [s.source for s in store.rows] == ["live", "cached"]
    assert store.rows[1].error.startswith("live_failed: HTTPStatusError")


# ---------------------------------------------------------------- fallback on failure
@pytest.mark.parametrize("mode,err", [("500", "HTTPStatusError"), ("timeout", "ReadTimeout"),
                                      ("garbage", "JSONDecodeError"), ("missing_fields", "KeyError")])
def test_failure_falls_back_to_cached_live_data_and_says_so(api, mode, err):
    store = MemoryWeatherSnapshots()
    make(api, snapshots=store).get("Pune")  # a good live result gets cached
    api.mode = mode
    later = NOW + timedelta(hours=2)
    r = make(api, snapshots=store, clock=lambda: later).get("Pune")
    assert_honest(r)
    assert r.source == "cached" and r.available and not r.stale and r.usable
    assert r.observed_at == datetime.fromisoformat("2026-10-01T10:00:00+05:30")  # original time, not "now"
    assert r.fetched_at == later
    assert err in r.error
    assert "not live" in r.source_label


def test_no_cache_falls_back_to_demo_labelled_demo(api):
    api.mode = "timeout"
    r = make(api).get("Pune")
    assert_honest(r)
    assert r.source == "demo" and r.provider == "demo dataset"
    assert "DEMO" in r.source_label and "not a real forecast" in r.source_label
    assert "ReadTimeout" in r.error


def test_no_cache_no_demo_is_unavailable(api):
    api.mode = "500"
    store = MemoryWeatherSnapshots()
    r = make(api, snapshots=store).get("Nagpur")
    assert_honest(r, "Nagpur")
    assert not r.available and r.source == "unavailable" and not r.usable
    assert store.rows[-1].source == "unavailable"


def test_old_cache_is_flagged_stale_and_policy_escalates(api):
    store = MemoryWeatherSnapshots()
    make(api, snapshots=store).get("Pune")
    api.mode = "500"
    r = make(api, snapshots=store, clock=lambda: NOW + timedelta(hours=7)).get("Pune")
    assert r.source == "cached" and r.stale and not r.usable
    assert "out of date" in r.source_label
    assert PolicyEngine(Settings()).decide_weather(r).state == DecisionState.EXPERT_REVIEW


def test_cache_always_serves_the_original_live_reading(api):
    """A cached fallback must never become the source of a later 'cached' result."""
    store = MemoryWeatherSnapshots()
    make(api, snapshots=store).get("Pune")
    api.mode = "500"
    for h in (1, 2, 3):
        r = make(api, snapshots=store, clock=lambda h=h: NOW + timedelta(hours=h)).get("Pune")
        assert r.observed_at == datetime.fromisoformat("2026-10-01T10:00:00+05:30")


def test_newer_live_reading_replaces_the_cache(api):
    store = MemoryWeatherSnapshots()
    make(api, snapshots=store).get("Pune")
    api.mode = "ok"
    api_payload = open_meteo_payload(temp=30.0, hour="2026-10-01T13:00")
    newer = make(lambda req: httpx.Response(200, json=api_payload), snapshots=store)
    newer.get("Pune")
    api.mode = "500"
    assert make(api, snapshots=store).get("Pune").temperature_c == 30.0


# ---------------------------------------------------------------- timeout
def test_default_timeout_is_eight_seconds():
    svc = WeatherService(Settings(_env_file=None))
    assert (svc.timeout.connect, svc.timeout.read) == (8.0, 8.0)


def test_timeout_is_passed_on_each_request(api):
    make(api).get("Pune")
    assert api.requests[0].extensions["timeout"]["read"] == LIVE.weather_timeout_s


def test_real_hanging_server_times_out_and_falls_back():
    """A real socket that accepts but never answers. Uses a 0.5 s timeout to keep the test fast."""
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen()
    held = []
    threading.Thread(target=lambda: held.append(srv.accept()), daemon=True).start()
    port = srv.getsockname()[1]
    try:
        settings = Settings(weather_live_enabled=True, weather_timeout_s=0.5,
                            open_meteo_url=f"http://127.0.0.1:{port}/v1/forecast")
        start = time.perf_counter()
        r = WeatherService(settings, snapshots=MemoryWeatherSnapshots(), clock=lambda: NOW).get("Pune")
        elapsed = time.perf_counter() - start
    finally:
        srv.close()
    assert elapsed < 2.0
    assert r.source == "demo" and "Timeout" in r.error


# ---------------------------------------------------------------- misc
def test_live_disabled_makes_no_request(api):
    r = make(api, settings=Settings(weather_live_enabled=False)).get("Pune")
    assert api.requests == [] and r.source == "demo" and r.error == "live_disabled"


def test_district_aliases_and_unknown(api):
    assert make(api).get("aurangabad").district == "Chhatrapati Sambhajinagar"
    store = MemoryWeatherSnapshots()
    r = make(api, snapshots=store).get("Atlantis")
    assert not r.available and r.error == "unknown_district" and store.rows == []


# ---------------------------------------------------------------- orchestrator + API
def test_weather_answer_tells_the_farmer_the_source(api):
    api.mode = "timeout"
    o = Orchestrator(Settings(), weather=make(api))
    r = o.run(CaseInput(crop="soybean", symptom_context="Will it rain in my area?"))
    assert r.state == DecisionState.PRELIMINARY_GUIDANCE
    assert "DEMO data for testing only, not a real forecast" in r.message
    assert r.calls[-1].output["source"] == "demo"  # logged in model_runs.output


SECRET = "test-secret-at-least-32-bytes-long!!"


def bearer():
    tok = jwt.encode({"sub": "7f1b1d1e-0000-4000-8000-000000000001", "aud": "authenticated",
                      "exp": int(time.time()) + 600}, SECRET, algorithm="HS256")
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture
def client(api):
    app.dependency_overrides[get_settings] = lambda: Settings(supabase_jwt_secret=SECRET)
    app.dependency_overrides[get_weather_service] = lambda: make(api)
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_api_weather(client, api):
    body = client.get("/api/weather", params={"district": "Pune"}, headers=bearer()).json()
    assert body["source"] == "live" and body["district"] == "Pune" and body["observed_at"]
    assert "Open-Meteo" in body["source_label"]


def test_api_weather_fallback_is_labelled(client, api):
    api.mode = "500"
    body = client.get("/api/weather", params={"district": "Pune"}, headers=bearer()).json()
    assert body["source"] == "demo" and "DEMO" in body["source_label"] and body["error"]


def test_api_weather_validation_and_auth(client):
    r = client.get("/api/weather", params={"district": "Atlantis"}, headers=bearer())
    assert r.status_code == 422 and "Pune" in r.json()["detail"]["districts"]
    assert client.get("/api/weather").status_code == 401
