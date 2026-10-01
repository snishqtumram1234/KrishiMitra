from datetime import date, datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.case import DecisionState
from app.schemas.orchestration import ConfidenceBand, OrchestratorResult, ReasonCode, TraceStep


class ImageKind(StrEnum):
    LEAF_CLOSEUP = "leaf_closeup"
    FIELD_OVERVIEW = "field_overview"


class CaseCreate(BaseModel):
    crop: str
    district: str = "Pune"
    # CLAUDE.md: symptom context is a required input; the intent router reads it.
    symptom_context: str = Field(min_length=1, max_length=2000)
    language: Literal["en", "mr"] = "en"
    growth_stage: str | None = Field(default=None, max_length=100)
    symptom_started_at: date | None = None
    recent_rainfall: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("crop")
    @classmethod
    def soybean_only(cls, v: str) -> str:
        if v.strip().lower() != "soybean":
            raise ValueError("Only soybean is supported in this version of KrishiMitra")
        return "soybean"

    @field_validator("symptom_started_at")
    @classmethod
    def not_in_future(cls, v: date | None) -> date | None:
        if v and v > date.today():
            raise ValueError("symptom_started_at cannot be in the future")
        return v


class ImageOut(BaseModel):
    id: UUID
    case_id: UUID
    kind: ImageKind
    storage_path: str
    content_type: str
    size_bytes: int
    created_at: datetime


class CaseOut(CaseCreate):
    id: UUID
    user_id: UUID
    # crop_check = created from the photo form (POST /api/cases); question = created by POST /api/questions
    entry_point: Literal["crop_check", "question"] = "crop_check"
    decision_state: DecisionState | None = None
    # Every photo uploaded to this case, oldest first. The newest of each kind is the one analysed.
    # Use these ids with GET /api/cases/{case_id}/images/{image_id}/signed-url.
    images: list[ImageOut] = Field(default_factory=list)
    created_at: datetime


class QuestionCreate(BaseModel):
    """POST /api/questions: ask a text question with no photo. The intent router decides what happens."""

    question: str = Field(min_length=1, max_length=2000)
    district: str = "Pune"
    language: Literal["en", "mr"] = "en"


class SignedUrlOut(BaseModel):
    image_id: UUID
    case_id: UUID
    kind: ImageKind
    content_type: str
    url: str  # short-lived; fetch it with a plain GET, no Authorization header
    expires_in: int  # seconds (always 300)
    expires_at: datetime


class AnalysisOut(BaseModel):
    """POST /analyze and GET /analysis."""

    routing_run_id: UUID
    case_id: UUID
    state: DecisionState
    result: OrchestratorResult
    created_at: datetime


class RunStep(BaseModel):
    step: str
    model_name: str
    latency_ms: int
    cost_usd: float
    confidence: float | None = None
    predicted_label: str | None = None
    outcome: str
    error: str | None = None


class RunTrace(BaseModel):
    """GET /api/runs/{routing_run_id}: the full route trace of one analysis."""

    routing_run_id: UUID
    case_id: UUID
    decision_state: DecisionState | None
    reason: str | None
    reason_code: ReasonCode | None
    reason_detail: str | None
    confidence_band: ConfidenceBand | None
    intent: str | None
    intent_confidence: float | None
    intent_rule: str | None
    path: str
    route_trace: list[str]
    trace: list[TraceStep]
    steps: list[RunStep]
    skipped_steps: list[str]
    estimated_cost_saved_usd: float
    total_latency_ms: int
    total_cost_usd: float
    created_at: datetime
