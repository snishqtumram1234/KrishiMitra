"""Expert workflow: escalations, reviews, farmer follow-ups, audit events.

One expert_reviews row per escalation:
  pending_review --(expert: likely | insufficient | unknown)--> reviewed
  pending_review --(expert: request_more)--> awaiting_farmer --(farmer follow-up)--> follow_up_received
A follow-up re-runs the orchestrator; if that escalates again, a new pending_review row is opened.
"""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.api import ImageOut
from app.schemas.case import Category, DecisionState
from app.schemas.orchestration import AdvisorySource


class ExpertStatus(StrEnum):
    PENDING_REVIEW = "pending_review"
    AWAITING_FARMER = "awaiting_farmer"
    REVIEWED = "reviewed"
    FOLLOW_UP_RECEIVED = "follow_up_received"


OPEN_STATUSES = {ExpertStatus.PENDING_REVIEW, ExpertStatus.AWAITING_FARMER}


class ReviewDecision(StrEnum):
    LIKELY = "likely"  # expert thinks a category is likely (still not a lab-confirmed diagnosis)
    INSUFFICIENT = "insufficient"  # not enough evidence to say anything
    REQUEST_MORE = "request_more"  # ask the farmer for more information / photos
    UNKNOWN = "unknown"  # expert cannot identify it


class Prediction(BaseModel):
    step: str
    model_name: str
    label: str | None = None
    confidence: float | None = None
    output: dict | list | None = None


class EscalationSnapshot(BaseModel):
    """Everything the expert needs, frozen at escalation time."""

    question: str
    description: str | None = None
    district: str
    growth_stage: str | None = None
    symptom_started_at: str | None = None
    recent_rainfall: str | None = None
    intent: str | None = None
    path: str | None = None
    images: list[ImageOut] = Field(default_factory=list)
    predictions: list[Prediction] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    sources: list[AdvisorySource] = Field(default_factory=list)
    follow_ups: list[str] = Field(default_factory=list)


class RecommendedAdvisory(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    publisher: str = Field(min_length=1, max_length=200)
    url: str | None = Field(default=None, max_length=500)


class ExpertReviewRecord(BaseModel):
    id: UUID
    case_id: UUID
    routing_run_id: UUID
    status: ExpertStatus
    escalation_reason: str
    snapshot: EscalationSnapshot
    decision: ReviewDecision | None = None
    label: Category | None = None
    notes: str | None = None
    recommended_advisory: RecommendedAdvisory | None = None
    reviewer_id: UUID | None = None
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ReviewIn(BaseModel):
    decision: ReviewDecision
    notes: str = Field(default="", max_length=4000)
    label: Category | None = None  # required when decision == likely
    recommended_advisory: RecommendedAdvisory | None = None

    @model_validator(mode="after")
    def check(self):
        if self.decision == ReviewDecision.LIKELY and self.label is None:
            raise ValueError("decision 'likely' needs a label (the category the expert considers likely)")
        if self.decision != ReviewDecision.LIKELY and self.label is not None:
            raise ValueError("label is only allowed with decision 'likely'")
        if self.decision == ReviewDecision.REQUEST_MORE and not self.notes.strip():
            raise ValueError("decision 'request_more' needs notes telling the farmer what to send")
        return self


class ExpertCaseSummary(BaseModel):
    case_id: UUID
    expert_review_id: UUID
    status: ExpertStatus
    escalation_reason: str
    district: str
    question: str
    decision_state: DecisionState | None = None
    created_at: datetime


class ExpertCaseDetail(BaseModel):
    case_id: UUID
    current: ExpertReviewRecord
    history: list[ExpertReviewRecord]  # newest first, includes current


class ExpertFeedback(BaseModel):
    """What the farmer sees about the expert side of their case."""

    status: ExpertStatus
    decision: ReviewDecision | None = None
    label: Category | None = None
    notes: str | None = None  # for request_more: what the expert wants from the farmer
    recommended_advisory: RecommendedAdvisory | None = None
    reviewed_at: datetime | None = None


class FollowUpRecord(BaseModel):
    id: UUID
    case_id: UUID
    answer: str | None = None
    image_id: UUID | None = None
    created_at: datetime


class AuditEvent(BaseModel):
    id: UUID
    event_type: str  # escalation_created | escalation_updated | expert_review_submitted | follow_up_submitted
    actor_id: UUID | None = None  # None = system (the orchestrator)
    actor_role: str  # system | farmer | expert
    case_id: UUID | None = None
    expert_review_id: UUID | None = None
    details: dict = Field(default_factory=dict)
    created_at: datetime
