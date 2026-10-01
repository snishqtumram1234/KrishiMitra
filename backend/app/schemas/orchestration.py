from datetime import UTC, date, datetime, timedelta, timezone
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, computed_field, model_validator

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


# The same three bands as Tier, named for clients. low < 0.60, medium 0.60 to 0.85 inclusive, high > 0.85.
ConfidenceBand = Literal["low", "medium", "high"]


class ReasonCode(StrEnum):
    """Stable machine codes for why a decision was made. Clients build their own (English / Marathi) text from
    these. `reason` in responses is `<code>` or `<code>:<detail>`; reason_code and reason_detail split it."""

    QUALITY_FAILED = "quality_failed"  # detail: the first quality issue
    CROP_NOT_SOYBEAN = "crop_not_soybean"
    FARMER_REQUESTED_EXPERT = "farmer_requested_expert"
    UNSUPPORTED_REQUEST = "unsupported_request"
    INTENT_UNCLEAR = "intent_unclear"
    TREATMENT_NEEDS_EXPERT = "treatment_needs_expert"
    TREATMENT_VERIFIED_SOURCE = "treatment_verified_source"
    WEATHER_CONTEXT = "weather_context"
    ADVISORY_LOOKUP = "advisory_lookup"
    GENERAL_CROP_QUESTION = "general_crop_question"
    LOW_CONFIDENCE_REQUEST_EVIDENCE = "low_confidence_request_evidence"
    LOW_CONFIDENCE_ESCALATE = "low_confidence_escalate"
    MODELS_CONFLICT = "models_conflict"
    LABEL_UNKNOWN = "label_unknown"
    MID_CONFIDENCE = "mid_confidence"
    HIGH_CONFIDENCE = "high_confidence"
    SOURCES_UNAVAILABLE = "sources_unavailable"  # detail: advisory | weather | vision_error | ...


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


# demo = placeholder or demo data. ingested = a real advisory document that was ingested and reviewed.
SourceType = Literal["demo", "ingested"]


class AdvisorySource(BaseModel):
    title: str
    publisher: str
    verified: bool
    stale: bool = False
    structured: bool = False  # machine-readable, reviewed record (required for anything treatment-related)
    source_type: SourceType = "demo"  # safe default: a source is demo until proven otherwise
    published_at: date | None = None  # when the SOURCE DOCUMENT was published (not when we fetched it)
    source_url: str | None = None
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))  # when WE fetched it

    @model_validator(mode="after")
    def only_ingested_documents_may_be_verified(self) -> "AdvisorySource":
        if self.verified and self.source_type != "ingested":
            raise ValueError(
                "Only ingested advisory documents may be verified=true; placeholder or demo sources "
                "must have verified=false and source_type='demo'"
            )
        return self


class AdvisoryResult(BaseModel):
    sources: list[AdvisorySource] = Field(default_factory=list)
    summary: str = ""

    @property
    def usable(self) -> bool:
        """At least one source, and every source is verified and fresh. Demo sources never are."""
        return bool(self.sources) and all(s.verified and not s.stale for s in self.sources)

    @property
    def demo_only(self) -> bool:
        return bool(self.sources) and all(s.source_type == "demo" for s in self.sources)


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


FollowUpAnswerType = Literal["choice", "photo", "text"]


class FollowUpOptions(BaseModel):
    """A structured follow-up question. The client renders its own wording per question_id and option code."""

    question_id: str  # leaf_position | field_overview_photo | describe_problem
    answer_type: FollowUpAnswerType  # choice: pick one of `options`; photo: upload; text: free text
    options: list[str] = Field(default_factory=list)


class PolicyDecision(BaseModel):
    state: DecisionState
    reason: str
    message: str  # English fallback text. Clients should build their own from the structured fields.
    follow_up_question: str | None = None  # English fallback text
    follow_up: FollowUpOptions | None = None


class CallLog(BaseModel):
    """One model/tool call. Mirrors routing_runs / model_runs columns."""

    route: str
    model: str
    latency_ms: int
    started_at_ms: int | None = None  # offset from the start of the analysis
    cost_usd: float = 0.0
    confidence: float | None = None
    outcome: str = "ok"  # ok | error
    error: str | None = None
    output: dict | list | None = None


TraceStatus = Literal["completed", "failed", "skipped"]


class TraceStep(BaseModel):
    """One step of the recorded run, in canonical order, ready for a client to replay."""

    step: str  # intent_router | quality_gate | vision | advisory | weather | policy_decision
    position: int  # canonical order: 0 intent_router ... 4 weather, 5 policy_decision
    status: TraceStatus
    model_name: str | None = None
    started_at_ms: int | None = None  # offset from analysis start; None when skipped
    latency_ms: int | None = None
    cost_usd: float = 0.0
    confidence: float | None = None
    confidence_band: ConfidenceBand | None = None  # vision step only
    outcome: str | None = None  # ok | error; None when skipped
    error: str | None = None
    skipped_reason: str | None = None  # route_does_not_use_step | stopped_earlier | confidence_not_high
    detail: dict = Field(default_factory=dict)  # structured per-step codes and numbers, no prose


class OrchestratorResult(BaseModel):
    state: DecisionState
    reason: str  # `<reason_code>` or `<reason_code>:<reason_detail>`
    reason_code: ReasonCode | None = None
    reason_detail: str | None = None
    message: str  # English fallback text
    follow_up_question: str | None = None  # English fallback text
    follow_up_options: FollowUpOptions | None = None
    # Always a preliminary observation, never a confirmed diagnosis.
    preliminary_label: Category | None = None
    confidence: float | None = None
    confidence_band: ConfidenceBand | None = None
    missing_information: list[str] = Field(default_factory=list)  # stable codes, most important first
    sources: list[AdvisorySource] = Field(default_factory=list)
    route_trace: list[str] = Field(default_factory=list)
    trace: list[TraceStep] = Field(default_factory=list)
    calls: list[CallLog] = Field(default_factory=list)
    total_latency_ms: int = 0
    total_cost_usd: float = 0.0
    intent: Intent | None = None
    intent_confidence: float | None = None
    intent_rule: str | None = None
    path: str | None = None  # which orchestration path ran, e.g. "image_diagnosis", "weather"
    skipped_steps: list[str] = Field(default_factory=list)
    estimated_cost_saved_usd: float = 0.0
