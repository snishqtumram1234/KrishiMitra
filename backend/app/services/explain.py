"""Structured explanation of an analysis: stable codes instead of prose, so any client (English, Marathi, or
anything later) can build its own wording. Pure functions, no I/O.

- split_reason / ReasonCode: why a decision was made.
- confidence band: low / medium / high.
- missing_information: codes for what would improve the answer.
- follow-up questions: id + answer type + option codes.
- build_trace: the recorded run in canonical step order, with real timings, for the client to replay.
"""

from app.schemas.case import CaseInput
from app.schemas.orchestration import (
    CallLog,
    ConfidenceBand,
    FollowUpOptions,
    ReasonCode,
    Tier,
    TraceStep,
)

# Canonical step order. position is the index here; policy_decision is always last.
PIPELINE = ("intent_router", "quality_gate", "vision", "advisory", "weather")
POLICY_STEP = "policy_decision"
POSITION = {step: i for i, step in enumerate((*PIPELINE, POLICY_STEP))}

TERMINAL_INTENT_PATHS = {"expert_escalation", "unsupported_request"}  # stop right after the intent check


# ---------------------------------------------------------------- reason codes and bands
def split_reason(reason: str) -> tuple[ReasonCode, str | None]:
    """'quality:blurry' -> (QUALITY_FAILED, 'blurry'); 'mid_confidence' -> (MID_CONFIDENCE, None)."""
    head, _, detail = reason.partition(":")
    if head == "quality":
        return ReasonCode.QUALITY_FAILED, detail or None
    return ReasonCode(head), detail or None


BAND_OF_TIER: dict[Tier, ConfidenceBand] = {Tier.LOW: "low", Tier.MID: "medium", Tier.HIGH: "high"}


# ---------------------------------------------------------------- follow-up questions
# question_id -> (answer_type, option codes). The English phrase for each option is only used as the stored
# answer text that is added to the case (and shown to experts).
FOLLOW_UP_QUESTIONS: dict[str, tuple[str, list[str]]] = {
    "leaf_position": ("choice", ["older_leaves", "younger_leaves", "both"]),
    "field_overview_photo": ("photo", []),
    "describe_problem": ("text", []),
}
OPTION_TEXT = {
    ("leaf_position", "older_leaves"): "older leaves",
    ("leaf_position", "younger_leaves"): "younger leaves",
    ("leaf_position", "both"): "both older and younger leaves",
}


def follow_up(question_id: str) -> FollowUpOptions:
    answer_type, options = FOLLOW_UP_QUESTIONS[question_id]
    return FollowUpOptions(question_id=question_id, answer_type=answer_type, options=list(options))


def validate_follow_up_choice(question_id: str | None, option: str | None) -> str | None:
    """Return an error message, or None if (question_id, option) is a valid structured answer."""
    if option is None and question_id is None:
        return None
    if question_id is None:
        return "option needs a question_id"
    if question_id not in FOLLOW_UP_QUESTIONS:
        return f"unknown question_id {question_id!r}"
    answer_type, options = FOLLOW_UP_QUESTIONS[question_id]
    if option is None:
        return None  # a question_id alone is fine (for text and photo answers)
    if answer_type != "choice":
        return f"question {question_id!r} does not take an option"
    if option not in options:
        return f"option {option!r} is not valid for question {question_id!r}"
    return None


# ---------------------------------------------------------------- missing information
# Stable codes. REQUIRED ones block or weaken the answer; OPTIONAL ones would just improve it.
MISSING_REQUIRED = {
    "close_up_photo",  # no usable close-up photo was received
    "clearer_close_up_photo",  # a photo was received but failed the quality check
    "symptom_description",  # the question was not understood
    "affected_leaf_position",  # older / younger / both (the mid-confidence follow-up)
    "verified_advisory_source",  # no verified advisory exists for this
    "current_weather",  # weather was unavailable
    "treatment_source",  # no verified structured treatment source exists
}
MISSING_OPTIONAL = {"field_overview_photo", "growth_stage", "symptom_start_date", "recent_rainfall"}
MISSING_CODES = sorted(MISSING_REQUIRED | MISSING_OPTIONAL)


def missing_information(reason_code: ReasonCode, detail: str | None, path: str | None, case: CaseInput) -> list[str]:
    """What is missing, most important first. Required codes come from the decision itself; optional ones
    (field photo, growth stage, start date, rainfall) are listed only for image diagnoses that got past the
    photo check."""
    out: list[str] = []
    if reason_code == ReasonCode.QUALITY_FAILED:
        out.append("close_up_photo" if detail in ("missing_image", "unreadable_image") else "clearer_close_up_photo")
    elif reason_code == ReasonCode.INTENT_UNCLEAR:
        out.append("symptom_description")
    elif reason_code == ReasonCode.LOW_CONFIDENCE_REQUEST_EVIDENCE:
        out.append("field_overview_photo")
    elif reason_code == ReasonCode.MID_CONFIDENCE:
        out.append("affected_leaf_position")
    elif reason_code == ReasonCode.SOURCES_UNAVAILABLE:
        if detail == "advisory":
            out.append("verified_advisory_source")
        elif detail == "weather":
            out.append("current_weather")
    elif reason_code == ReasonCode.TREATMENT_NEEDS_EXPERT:
        out.append("treatment_source")

    if path == "image_diagnosis" and reason_code != ReasonCode.QUALITY_FAILED:
        if case.field_overview_image is None and "field_overview_photo" not in out:
            out.append("field_overview_photo")
        if not case.growth_stage:
            out.append("growth_stage")
        if not case.symptom_started_at:
            out.append("symptom_start_date")
        if not case.rainfall:
            out.append("recent_rainfall")
    return out


# ---------------------------------------------------------------- trace
def skip_reason(step: str, path: str | None, tier: Tier | None) -> str:
    if path in (None, *TERMINAL_INTENT_PATHS):
        return "stopped_earlier"
    if path == "image_diagnosis":
        if step == "weather" and tier == Tier.MID:
            return "confidence_not_high"
        return "stopped_earlier"
    return "route_does_not_use_step"  # weather / treatment_safety / advisory / general routes use few steps


def _detail(call: CallLog, band: ConfidenceBand | None) -> dict:
    out = call.output
    if call.outcome != "ok" or out is None:
        return {}
    if call.route == "intent_router" and isinstance(out, dict):
        return {k: out.get(k) for k in ("intent", "confidence", "rule", "matched")}
    if call.route == "quality_gate" and isinstance(out, dict):
        return {k: out.get(k) for k in ("passed", "score", "issues", "next_action", "details")}
    if call.route == "vision" and isinstance(out, list) and out:
        top = max(out, key=lambda r: r.get("confidence", 0.0))
        return {"label": top.get("label"), "confidence": top.get("confidence"), "confidence_band": band,
                "model_count": len(out)}
    if call.route == "advisory" and isinstance(out, dict):
        sources = out.get("sources") or []
        return {
            "source_count": len(sources),
            "verified_count": sum(1 for s in sources if s.get("verified")),
            "demo_count": sum(1 for s in sources if s.get("source_type", "demo") == "demo"),
        }
    if call.route == "weather" and isinstance(out, dict):
        return {k: out.get(k) for k in ("source", "available", "stale")}
    return {}


def build_trace(
    calls: list[CallLog],
    *,
    path: str | None,
    tier: Tier | None,
    vision_band: ConfidenceBand | None,
    state: str,
    reason_code: ReasonCode,
    reason_detail: str | None,
    confidence_band: ConfidenceBand | None,
) -> list[TraceStep]:
    """Every pipeline step (completed, failed or skipped) in canonical order, then the policy decision."""
    by_step = {c.route: c for c in calls}
    steps: list[TraceStep] = []
    for step in PIPELINE:
        c = by_step.get(step)
        if c is None:
            steps.append(TraceStep(step=step, position=POSITION[step], status="skipped",
                                   skipped_reason=skip_reason(step, path, tier)))
            continue
        band = vision_band if step == "vision" else None
        steps.append(TraceStep(
            step=step, position=POSITION[step], status="completed" if c.outcome == "ok" else "failed",
            model_name=c.model, started_at_ms=c.started_at_ms, latency_ms=c.latency_ms, cost_usd=c.cost_usd,
            confidence=c.confidence, confidence_band=band, outcome=c.outcome, error=c.error, detail=_detail(c, band),
        ))
    end = max((c.started_at_ms or 0) + c.latency_ms for c in calls) if calls else 0
    steps.append(TraceStep(
        step=POLICY_STEP, position=POSITION[POLICY_STEP], status="completed", model_name="policy-engine",
        started_at_ms=end, latency_ms=0, outcome="ok",
        detail={"state": state, "reason_code": reason_code.value, "reason_detail": reason_detail,
                "confidence_band": confidence_band},
    ))
    return steps
