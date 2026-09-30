from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, computed_field

from app.schemas.case import Category, DecisionState


class Intent(StrEnum):
    CROP_HEALTH_IMAGE = "crop_health_image"
    GENERAL_CROP_QUESTION = "general_crop_question"
    WEATHER_CONTEXT = "weather_context"
    ADVISORY_LOOKUP = "advisory_lookup"
    TREATMENT_SAFETY = "treatment_safety"
    EXPERT_ESCALATION = "expert_escalation"
    UNSUPPORTED_REQUEST = "unsupported_request"


class Tier(StrEnum):
    LOW = "low"  # < 0.60
    MID = "mid"  # 0.60 - 0.85
    HIGH = "high"  # > 0.85


class QualityResult(BaseModel):
    passed: bool
    score: int = Field(ge=0, le=100)  # 0-100, the weakest sub-check
    # missing_image, unreadable_image, too_small, too_dark, too_bright, blurry, no_leaf_detected
    issues: list[str] = Field(default_factory=list)
    next_action: str = "continue"  # continue | upload_image | retake_* (machine-readable, for the UI)
    details: dict | None = None  # raw measurements and sub-scores

    @property
    def reason(self) -> str | None:
        return self.issues[0] if self.issues else None


class IntentResult(BaseModel):
    intent: Intent
    confidence: float = Field(ge=0.0, le=1.0)
    rule: str  # e.g. "guard:treatment_safety", "keywords:weather_context", "fallback:no_match"
    matched: list[str] = Field(default_factory=list)


class VisionResult(BaseModel):
    model_name: str
    label: Category
    confidence: float = Field(ge=0.0, le=1.0)


class AdvisorySource(BaseModel):
    title: str
    publisher: str
    verified: bool
    stale: bool = False
    structured: bool = False  # machine-readable, reviewed record (required for anything treatment-related)


class AdvisoryResult(BaseModel):
    sources: list[AdvisorySource] = Field(default_factory=list)
    summary: str = ""

    @property
    def usable(self) -> bool:
        return bool(self.sources) and all(s.verified and not s.stale for s in self.sources)


WeatherSource = Literal["live", "cached", "demo", "unavailable"]
IST = timezone(timedelta(hours=5, minutes=30))


class WeatherResult(BaseModel):
    available: bool
    source: WeatherSource = "unavailable"
    provider: str | None = None  # "Open-Meteo" or "demo dataset". Never claim IMD.
    district: str | None = None
    observed_at: datetime | None = None  # time the data describes (not when we fetched it)
    fetched_at: datetime | None = None
    stale: bool = False
    temperature_c: float | None = None
    humidity_pct: float | None = None
    precipitation_mm: float | None = None  # current
    rain_next_24h_mm: float | None = None
    rain_probability_max_pct: float | None = None
    wind_speed_kmh: float | None = None
    error: str | None = None  # why the live source was not used, if it was not
    summary: str = ""

    @property
    def usable(self) -> bool:
        return self.available and not self.stale

    @computed_field
    @property
    def source_label(self) -> str:
        """Human-readable provenance, shown to farmers and returned by the API."""
        when = self.observed_at.astimezone(IST).strftime("%d %b %H:%M IST") if self.observed_at else "unknown time"
        if self.source == "live":
            return f"{self.provider} forecast-model data (live), for {when}"
        if self.source == "cached":
            stale = ", out of date" if self.stale else ""
            return f"{self.provider} data cached from {when} (not live{stale})"
        if self.source == "demo":
            return "DEMO data for testing only, not a real forecast"
        return "no weather data available"


class PolicyDecision(BaseModel):
    state: DecisionState
    reason: str
    message: str
    follow_up_question: str | None = None


class CallLog(BaseModel):
    """One model/tool call. Mirrors routing_runs / model_runs columns."""

    route: str
    model: str
    latency_ms: int
    cost_usd: float = 0.0
    confidence: float | None = None
    outcome: str = "ok"  # ok | error
    error: str | None = None
    output: dict | list | None = None


class OrchestratorResult(BaseModel):
    state: DecisionState
    reason: str
    message: str
    follow_up_question: str | None = None
    # Always a preliminary observation, never a confirmed diagnosis.
    preliminary_label: Category | None = None
    confidence: float | None = None
    sources: list[AdvisorySource] = Field(default_factory=list)
    route_trace: list[str] = Field(default_factory=list)
    calls: list[CallLog] = Field(default_factory=list)
    total_latency_ms: int = 0
    total_cost_usd: float = 0.0
    intent: Intent | None = None
    intent_confidence: float | None = None
    intent_rule: str | None = None
    path: str | None = None  # which orchestration path ran, e.g. "image_diagnosis", "weather"
    skipped_steps: list[str] = Field(default_factory=list)
    estimated_cost_saved_usd: float = 0.0
