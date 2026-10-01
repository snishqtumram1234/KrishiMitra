from enum import StrEnum

from pydantic import BaseModel


class DecisionState(StrEnum):
    NEEDS_BETTER_IMAGE = "NEEDS_BETTER_IMAGE"
    NEEDS_MORE_CONTEXT = "NEEDS_MORE_CONTEXT"
    PRELIMINARY_GUIDANCE = "PRELIMINARY_GUIDANCE"
    EXPERT_REVIEW = "EXPERT_REVIEW"
    UNSUPPORTED = "UNSUPPORTED"


class Category(StrEnum):
    HEALTHY = "healthy"
    RUST_LIKE = "rust_like"
    LEAF_SPOT_LIKE = "leaf_spot_like"
    INSECT_DAMAGE = "insect_damage"
    UNKNOWN = "unknown"


class CaseInput(BaseModel):
    # Required
    crop: str
    district: str = "Pune"
    symptom_context: str
    close_up_image: bytes | None = None
    # Optional
    field_overview_image: bytes | None = None
    growth_stage: str | None = None
    symptom_started_at: str | None = None  # ISO date
    rainfall: str | None = None
    description: str | None = None
    language: str = "en"  # "en" | "mr"
