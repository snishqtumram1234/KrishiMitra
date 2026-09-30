"""Row shapes for routing_runs / model_runs (supabase/migrations/).

routing_runs: one row per analysis. model_runs: one row per model/tool call in that analysis.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.case import DecisionState


class RoutingRunRecord(BaseModel):
    id: UUID
    case_id: UUID
    route: str  # orchestration path: image_diagnosis | weather | treatment_safety | advisory_lookup | ...
    intent: str | None = None
    decision_state: DecisionState | None = None
    confidence: float | None = None
    reason: str | None = None
    latency_ms: int
    cost_usd: float
    outcome: str  # ok | degraded (a call errored)
    details: dict | None = None  # {"result": OrchestratorResult json}
    created_at: datetime


class ModelRunRecord(BaseModel):
    id: UUID
    routing_run_id: UUID
    case_id: UUID
    step: str
    model_name: str
    model_version: str | None = None
    output: dict | list | None = None
    predicted_label: str | None = None
    confidence: float | None = None
    latency_ms: int
    cost_usd: float
    outcome: str
    error: str | None = None
    created_at: datetime


class WeatherSnapshotRecord(BaseModel):
    """One row of weather_snapshots: every weather result we produce, whatever its source."""

    id: UUID
    district: str
    source: str  # live | cached | demo | unavailable
    provider: str | None = None
    observed_at: datetime | None = None
    fetched_at: datetime
    stale: bool = False
    temperature_c: float | None = None
    humidity_pct: float | None = None
    precipitation_mm: float | None = None
    rain_next_24h_mm: float | None = None
    rain_probability_max_pct: float | None = None
    wind_speed_kmh: float | None = None
    error: str | None = None
    created_at: datetime

