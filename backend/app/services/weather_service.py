"""Weather adapter: live Open-Meteo -> cached live snapshot -> demo dataset -> unavailable.

- live:   Open-Meteo forecast API (free, no key). This is forecast-model data from Open-Meteo,
          NOT IMD, and is labelled as such. Hard 3 s timeout (WEATHER_TIMEOUT_S).
- cached: the most recent *live* snapshot for the district from weather_snapshots, re-served
          with its original observed_at; flagged stale after WEATHER_CACHE_MAX_AGE_HOURS.
- demo:   data/demo-cases/weather/<district>.json, illustrative values, labelled DEMO.

Every result carries source, observed_at and district, and is stored in weather_snapshots.
If the live call fails, `error` says why, so the fallback is never silent.
"""

import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Protocol
from uuid import uuid4

import httpx

from app.config import Settings, get_settings
from app.schemas.orchestration import WeatherResult
from app.schemas.runs import WeatherSnapshotRecord
from app.services.districts import District, resolve_district

log = logging.getLogger(__name__)
DEMO_DIR = Path(__file__).resolve().parents[3] / "data" / "demo-cases" / "weather"
PROVIDER_LIVE = "Open-Meteo"
PROVIDER_DEMO = "demo dataset"


class WeatherSnapshotStore(Protocol):
    def save_weather_snapshot(self, snap: WeatherSnapshotRecord) -> None: ...
    def latest_live_weather(self, district: str) -> WeatherSnapshotRecord | None: ...


class MemoryWeatherSnapshots:
    def __init__(self) -> None:
        self.rows: list[WeatherSnapshotRecord] = []

    def save_weather_snapshot(self, snap: WeatherSnapshotRecord) -> None:
        self.rows.append(snap)

    def latest_live_weather(self, district: str) -> WeatherSnapshotRecord | None:
        live = [r for r in self.rows if r.district == district and r.source == "live"]
        return max(live, key=lambda r: r.observed_at, default=None)


def _summary(r: WeatherResult) -> str:
    now = []
    if r.temperature_c is not None:
        now.append(f"{r.temperature_c:.0f}°C")
    if r.humidity_pct is not None:
        now.append(f"humidity {r.humidity_pct:.0f}%")
    text = f"{r.district}: now {', '.join(now)}." if now else f"{r.district}."
    if r.rain_next_24h_mm is not None:
        chance = f" (chance up to {r.rain_probability_max_pct:.0f}%)" if r.rain_probability_max_pct is not None else ""
        text += f" Rain expected in the next 24 hours: {r.rain_next_24h_mm:.0f} mm{chance}."
    return text


class WeatherService:
    model_name = "weather-adapter"

    def __init__(
        self,
        settings: Settings | None = None,
        snapshots: WeatherSnapshotStore | None = None,
        client: httpx.Client | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        demo_dir: Path = DEMO_DIR,
    ):
        s = settings or get_settings()
        self.live_enabled = s.weather_live_enabled
        self.url = s.open_meteo_url
        self.max_age = timedelta(hours=s.weather_cache_max_age_hours)
        self.snapshots = snapshots or MemoryWeatherSnapshots()
        self.timeout = httpx.Timeout(s.weather_timeout_s)
        self._client = client  # created lazily: building a TLS client is slow and most runs never need it
        self._clock = clock
        self._demo_dir = demo_dir

    # ---------------------------------------------------------------- public
    def get(self, district: str) -> WeatherResult:
        now = self._clock()
        d = resolve_district(district)
        if d is None:
            return self._finish(WeatherResult(available=False, district=district, fetched_at=now,
                                              error="unknown_district", summary=""), store=False)

        error = "live_disabled"
        if self.live_enabled:
            try:
                return self._finish(self._live(d, now))
            except (httpx.HTTPError, ValueError, KeyError, TypeError, IndexError) as e:
                error = f"live_failed: {type(e).__name__}: {e}"[:300]

        if cached := self.snapshots.latest_live_weather(d.name):
            return self._finish(self._from_cache(cached, now, error))
        if demo := self._demo(d, now, error):
            return self._finish(demo)
        return self._finish(WeatherResult(available=False, district=d.name, fetched_at=now, error=error))

    @property
    def _http(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout)
        return self._client

    # ---------------------------------------------------------------- sources
    def _live(self, d: District, now: datetime) -> WeatherResult:
        r = self._http.get(self.url, timeout=self.timeout, params={
            "latitude": d.lat,
            "longitude": d.lon,
            "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
            "hourly": "precipitation",
            "daily": "precipitation_probability_max",
            "forecast_days": 2,
            "timezone": "Asia/Kolkata",
        })
        r.raise_for_status()
        data = r.json()
        tz = timezone(timedelta(seconds=data["utc_offset_seconds"]))
        cur = data["current"]
        observed = datetime.fromisoformat(cur["time"]).replace(tzinfo=tz)
        hour = observed.replace(minute=0, second=0, microsecond=0)
        hourly = zip(data["hourly"]["time"], data["hourly"]["precipitation"], strict=True)
        next_24h = sum(p or 0.0 for t, p in hourly
                       if hour <= datetime.fromisoformat(t).replace(tzinfo=tz) < hour + timedelta(hours=24))
        probs = [p for p in data["daily"]["precipitation_probability_max"] if p is not None]
        return WeatherResult(
            available=True,
            source="live",
            provider=PROVIDER_LIVE,
            district=d.name,
            observed_at=observed,
            fetched_at=now,
            temperature_c=cur["temperature_2m"],
            humidity_pct=cur["relative_humidity_2m"],
            precipitation_mm=cur["precipitation"],
            rain_next_24h_mm=round(next_24h, 1),
            rain_probability_max_pct=max(probs) if probs else None,
            wind_speed_kmh=cur["wind_speed_10m"],
        )

    def _from_cache(self, snap: WeatherSnapshotRecord, now: datetime, error: str) -> WeatherResult:
        return WeatherResult(
            available=True,
            source="cached",
            provider=snap.provider,
            district=snap.district,
            observed_at=snap.observed_at,  # the original time, never "now"
            fetched_at=now,
            stale=now - snap.observed_at > self.max_age,
            temperature_c=snap.temperature_c,
            humidity_pct=snap.humidity_pct,
            precipitation_mm=snap.precipitation_mm,
            rain_next_24h_mm=snap.rain_next_24h_mm,
            rain_probability_max_pct=snap.rain_probability_max_pct,
            wind_speed_kmh=snap.wind_speed_kmh,
            error=error,
        )

    def _demo(self, d: District, now: datetime, error: str) -> WeatherResult | None:
        path = self._demo_dir / f"{d.name.lower().replace(' ', '_')}.json"
        if not path.exists():
            return None
        raw = json.loads(path.read_text(encoding="utf-8"))
        return WeatherResult(
            available=True,
            source="demo",
            provider=PROVIDER_DEMO,
            district=d.name,
            observed_at=datetime.fromisoformat(raw["observed_at"]),
            fetched_at=now,
            temperature_c=raw.get("temperature_c"),
            humidity_pct=raw.get("humidity_pct"),
            precipitation_mm=raw.get("precipitation_mm"),
            rain_next_24h_mm=raw.get("rain_next_24h_mm"),
            rain_probability_max_pct=raw.get("rain_probability_max_pct"),
            wind_speed_kmh=raw.get("wind_speed_kmh"),
            error=error,
        )

    # ---------------------------------------------------------------- store every result
    def _finish(self, r: WeatherResult, store: bool = True) -> WeatherResult:
        r = r.model_copy(update={"summary": _summary(r) if r.available else ""})
        if store:
            self._save(WeatherSnapshotRecord(
                id=uuid4(),
                created_at=self._clock(),
                **r.model_dump(include={
                    "district", "source", "provider", "observed_at", "fetched_at", "stale", "temperature_c",
                    "humidity_pct", "precipitation_mm", "rain_next_24h_mm", "rain_probability_max_pct",
                    "wind_speed_kmh", "error",
                }),
            ))
        return r

    def _save(self, snap: WeatherSnapshotRecord) -> None:
        """Keeping a snapshot is a cache, not part of the answer: if the database write fails, log it and still return
        the weather. Otherwise one failed insert would discard good weather and send every case to an expert."""
        try:
            self.snapshots.save_weather_snapshot(snap)
        except Exception:  # noqa: BLE001 - any storage failure; the weather itself is still valid
            log.warning("could not save the weather snapshot for %s", snap.district, exc_info=True)
