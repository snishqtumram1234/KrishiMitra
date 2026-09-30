from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.case import DecisionState


class ImageKind(StrEnum):
    CLOSE_UP_LEAF = "close_up_leaf"
    FIELD_OVERVIEW = "field_overview"


class CaseCreate(BaseModel):
    crop: str = Field(min_length=1)
    district: str = "Pune"
    symptom_context: str = Field(min_length=1)
    language: Literal["en", "mr"] = "en"
    growth_stage: str | None = None
    rainfall: str | None = None
    description: str | None = None


class CaseOut(CaseCreate):
    id: UUID
    decision_state: DecisionState | None = None
    created_at: datetime


class ImageOut(BaseModel):
    id: UUID
    case_id: UUID
    kind: ImageKind
    content_type: str
    size_bytes: int
    created_at: datetime
