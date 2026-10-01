"""Expert-only endpoints. Every route requires a valid JWT whose app_metadata.role is "expert"."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.auth import AuthUser, require_expert
from app.api.deps import get_store
from app.schemas.expert import (
    ExpertCaseDetail,
    ExpertCaseSummary,
    ExpertReviewRecord,
    ExpertStatus,
    ReviewIn,
)
from app.services.case_store import CaseStore
from app.services.expert_service import ExpertService
from app.services.explain import split_reason

router = APIRouter(prefix="/api/expert/cases", tags=["expert"], dependencies=[Depends(require_expert)])


@router.get("", response_model=list[ExpertCaseSummary])
def list_expert_cases(
    status_filter: Literal["pending_review", "awaiting_farmer", "reviewed", "follow_up_received", "all"] = Query(
        "pending_review", alias="status"),
    store: CaseStore = Depends(get_store),
):
    statuses = None if status_filter == "all" else {ExpertStatus(status_filter)}
    out = []
    for rec in store.list_expert_reviews(statuses=statuses):
        case = store.get_case(rec.case_id)
        code, detail = split_reason(rec.escalation_reason)
        out.append(ExpertCaseSummary(
            case_id=rec.case_id, expert_review_id=rec.id, status=rec.status,
            escalation_reason=rec.escalation_reason, escalation_reason_code=code,
            escalation_reason_detail=detail, district=rec.snapshot.district,
            question=rec.snapshot.question, decision_state=case.decision_state if case else None,
            image_ids=[i.id for i in rec.snapshot.images], created_at=rec.created_at,
        ))
    return out


@router.get("/{case_id}", response_model=ExpertCaseDetail)
def get_expert_case(case_id: UUID, store: CaseStore = Depends(get_store)):
    history = store.list_expert_reviews(case_id)
    if not history:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No escalation for this case")
    code, detail = split_reason(history[0].escalation_reason)
    return ExpertCaseDetail(case_id=case_id, escalation_reason_code=code, escalation_reason_detail=detail,
                            current=history[0], history=history)


@router.post("/{case_id}/review", response_model=ExpertReviewRecord)
def review_case(
    case_id: UUID,
    body: ReviewIn,
    expert: AuthUser = Depends(require_expert),
    store: CaseStore = Depends(get_store),
):
    if not store.list_expert_reviews(case_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No escalation for this case")
    rec = ExpertService(store).review(case_id, expert.id, body)
    if rec is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This case has no escalation waiting for review")
    return rec
