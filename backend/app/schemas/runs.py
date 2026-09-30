"""Row shapes for the routing_runs / model_runs tables (supabase/migrations/..._core_case_tables.sql)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.case import DecisionState


class RoutingRunRecord(BaseModel):
    """One orchestrator step: a service call, or the final policy decision."""

    id: UUID
    case_id: UUID
    route: str
    intent: str | None = None
    decision_state: DecisionState | None = None
    confidence: float | None = None
    reason: str | None = None
    latency_ms: int
    cost_usd: float
    outcome: str
    details: dict | None = None
    created_at: datetime


class ModelRunRecord(BaseModel):
    """One model/tool call, linked to the routing step that made it."""

    id: UUID
    routing_run_id: UUID
    case_id: UUID
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
