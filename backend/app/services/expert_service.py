"""Expert workflow: open/refresh escalations, record expert reviews and farmer follow-ups, audit all of it."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.schemas.api import CaseOut
from app.schemas.expert import (
    AuditEvent,
    EscalationSnapshot,
    ExpertFeedback,
    ExpertReviewRecord,
    ExpertStatus,
    FollowUpRecord,
    Prediction,
    ReviewDecision,
    ReviewIn,
)
from app.schemas.orchestration import OrchestratorResult
from app.schemas.runs import ModelRunRecord, RoutingRunRecord
from app.services.case_store import CaseStore

# What an expert (and the farmer) would need, keyed by the policy's escalation reason.
MISSING_BY_REASON = {
    "low_confidence_escalate": "clearer or additional close-up photos of affected leaves",
    "models_conflict": "expert visual assessment (model outputs disagree)",
    "label_unknown": "expert identification (symptoms do not match a supported category)",
    "treatment_needs_expert": "a verified treatment source for this question",
    "farmer_requested_expert": "farmer asked to speak to an expert",
    "sources_unavailable:advisory": "a verified advisory source for this symptom",
    "sources_unavailable:weather": "current weather for the district",
    "sources_unavailable:vision_error": "vision model output (the model call failed)",
    "sources_unavailable:quality_gate_error": "image quality check (the check failed)",
    "sources_unavailable:intent_router_error": "question classification (the router failed)",
}
OPTIONAL_CASE_FIELDS = {
    "growth_stage": "growth stage",
    "symptom_started_at": "when the symptoms started",
    "recent_rainfall": "recent rainfall",
}


def _now() -> datetime:
    return datetime.now(UTC)


class ExpertService:
    def __init__(self, store: CaseStore):
        self.store = store

    # ---------------------------------------------------------------- audit
    def audit(self, event_type: str, actor_role: str, case_id: UUID | None, actor_id: UUID | None = None,
              expert_review_id: UUID | None = None, **details) -> None:
        self.store.save_audit_event(AuditEvent(
            id=uuid4(), event_type=event_type, actor_id=actor_id, actor_role=actor_role, case_id=case_id,
            expert_review_id=expert_review_id, details=details, created_at=_now(),
        ))

    # ---------------------------------------------------------------- escalation
    def snapshot(self, case: CaseOut, result: OrchestratorResult, model_runs: list[ModelRunRecord]) -> EscalationSnapshot:
        missing = [MISSING_BY_REASON[result.reason]] if result.reason in MISSING_BY_REASON else []
        if not any(i.kind == "field_overview" for i in self.store.list_images(case.id)):
            missing.append("field overview photo")
        missing += [label for field, label in OPTIONAL_CASE_FIELDS.items() if getattr(case, field) is None]
        predictions = [
            Prediction(step=m.step, model_name=m.model_name, label=m.predicted_label, confidence=m.confidence,
                       output=m.output)
            for m in model_runs if m.step in ("vision", "quality_gate", "intent_router")
        ]
        return EscalationSnapshot(
            question=case.symptom_context,
            description=case.description,
            district=case.district,
            growth_stage=case.growth_stage,
            symptom_started_at=case.symptom_started_at.isoformat() if case.symptom_started_at else None,
            recent_rainfall=case.recent_rainfall,
            intent=result.intent.value if result.intent else None,
            path=result.path,
            images=self.store.list_images(case.id),
            predictions=predictions,
            missing_information=missing,
            sources=result.sources,
            follow_ups=[f.answer for f in self.store.list_follow_ups(case.id) if f.answer],
        )

    def escalate(self, case: CaseOut, run: RoutingRunRecord, result: OrchestratorResult,
                 model_runs: list[ModelRunRecord]) -> ExpertReviewRecord:
        """Open a pending_review escalation, or refresh the one that is already pending."""
        snap = self.snapshot(case, result, model_runs)
        pending = self.store.list_expert_reviews(case.id, {ExpertStatus.PENDING_REVIEW})
        now = _now()
        if pending:
            rec = pending[0].model_copy(update={
                "routing_run_id": run.id, "escalation_reason": result.reason, "snapshot": snap, "updated_at": now,
            })
            self.store.update_expert_review(rec)
            self.audit("escalation_updated", "system", case.id, expert_review_id=rec.id,
                       routing_run_id=str(run.id), reason=result.reason)
            return rec
        rec = ExpertReviewRecord(
            id=uuid4(), case_id=case.id, routing_run_id=run.id, status=ExpertStatus.PENDING_REVIEW,
            escalation_reason=result.reason, snapshot=snap, created_at=now, updated_at=now,
        )
        self.store.save_expert_review(rec)
        self.audit("escalation_created", "system", case.id, expert_review_id=rec.id,
                   routing_run_id=str(run.id), reason=result.reason)
        return rec

    # ---------------------------------------------------------------- expert review
    def review(self, case_id: UUID, reviewer_id: UUID, body: ReviewIn) -> ExpertReviewRecord | None:
        """Apply a review to the case's pending escalation. None if nothing is pending."""
        pending = self.store.list_expert_reviews(case_id, {ExpertStatus.PENDING_REVIEW})
        if not pending:
            return None
        now = _now()
        status = ExpertStatus.AWAITING_FARMER if body.decision == ReviewDecision.REQUEST_MORE else ExpertStatus.REVIEWED
        rec = pending[0].model_copy(update={
            "status": status, "decision": body.decision, "label": body.label, "notes": body.notes or None,
            "recommended_advisory": body.recommended_advisory, "reviewer_id": reviewer_id,
            "reviewed_at": now, "updated_at": now,
        })
        self.store.update_expert_review(rec)
        self.audit("expert_review_submitted", "expert", case_id, actor_id=reviewer_id, expert_review_id=rec.id,
                   decision=body.decision.value, label=body.label.value if body.label else None,
                   status=status.value, has_recommended_advisory=body.recommended_advisory is not None)
        return rec

    # ---------------------------------------------------------------- farmer follow-up
    def record_follow_up(self, case: CaseOut, farmer_id: UUID, answer: str | None, image_id: UUID | None) -> None:
        self.store.add_follow_up(FollowUpRecord(id=uuid4(), case_id=case.id, answer=answer, image_id=image_id,
                                                created_at=_now()))
        closed = []
        for rec in self.store.list_expert_reviews(case.id, {ExpertStatus.AWAITING_FARMER}):
            self.store.update_expert_review(rec.model_copy(update={
                "status": ExpertStatus.FOLLOW_UP_RECEIVED, "updated_at": _now()}))
            closed.append(str(rec.id))
        self.audit("follow_up_submitted", "farmer", case.id, actor_id=farmer_id,
                   has_answer=bool(answer), image_id=str(image_id) if image_id else None,
                   answered_expert_requests=closed)

    def feedback(self, case_id: UUID) -> ExpertFeedback | None:
        rows = self.store.list_expert_reviews(case_id)
        if not rows:
            return None
        r = rows[0]
        return ExpertFeedback(status=r.status, decision=r.decision, label=r.label, notes=r.notes,
                              recommended_advisory=r.recommended_advisory, reviewed_at=r.reviewed_at)

