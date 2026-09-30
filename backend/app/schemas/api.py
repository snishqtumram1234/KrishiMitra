from datetime import date, datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.case import DecisionState
from app.schemas.orchestration import OrchestratorResult


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


class CaseOut(CaseCreate):
    id: UUID
    user_id: UUID
    decision_state: DecisionState | None = None
    created_at: datetime


class ImageOut(BaseModel):
    id: UUID
    case_id: UUID
    kind: ImageKind
    storage_path: str
    content_type: str
    size_bytes: int
    created_at: datetime


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
    route_trace: list[str]
    steps: list[RunStep]
    skipped_steps: list[str]
    estimated_cost_saved_usd: float
    total_latency_ms: int
    total_cost_usd: float
    created_at: datetime
