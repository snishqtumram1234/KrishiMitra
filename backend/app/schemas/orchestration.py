from enum import StrEnum

from pydantic import BaseModel, Field

from app.schemas.case import Category, DecisionState


class Intent(StrEnum):
    DIAGNOSIS = "diagnosis"
    GENERAL_ADVICE = "general_advice"
    UNKNOWN = "unknown"


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


class AdvisoryResult(BaseModel):
    sources: list[AdvisorySource] = Field(default_factory=list)
    summary: str = ""

    @property
    def usable(self) -> bool:
        return bool(self.sources) and all(s.verified and not s.stale for s in self.sources)


class WeatherResult(BaseModel):
    available: bool
    stale: bool = False
    summary: str = ""

    @property
    def usable(self) -> bool:
        return self.available and not self.stale


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
    skipped_steps: list[str] = Field(default_factory=list)
    estimated_cost_saved_usd: float = 0.0
