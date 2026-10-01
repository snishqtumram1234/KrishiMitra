"""Pure routing/safety policy (CLAUDE.md "Routing policy"). No I/O, no model calls.

Each check_* returns a terminal PolicyDecision, or None to continue.
No output of this module ever contains treatment or dosage advice.
"""

from app.config import Settings
from app.schemas.case import Category, DecisionState
from app.schemas.orchestration import (
    AdvisoryResult,
    ConfidenceBand,
    Intent,
    IntentResult,
    PolicyDecision,
    QualityResult,
    Tier,
    VisionResult,
    WeatherResult,
)
from app.services.explain import BAND_OF_TIER, follow_up

DISCLAIMER = "This is a preliminary observation, not a confirmed diagnosis."
NO_DOSE = "KrishiMitra does not give pesticide names or doses."
DEMO_NOTE = "The reference text comes from a demo source and is not verified."
INTENT_MIN_CONFIDENCE = 0.5

QUALITY_TIPS = {
    "missing_image": "No photo was received.",
    "unreadable_image": "The file could not be opened as a photo; please send a JPEG or PNG.",
    "too_small": "The photo is too small; move closer so the leaf fills most of the frame.",
    "too_dark": "The photo is too dark; take it in daylight.",
    "too_bright": "The photo is overexposed; avoid direct glare or shade the leaf.",
    "blurry": "The photo is blurry; hold the phone steady and tap the leaf to focus.",
    "no_leaf_detected": "We could not find a leaf; fill most of the frame with one soybean leaf.",
}


class PolicyEngine:
    def __init__(self, settings: Settings):
        self.low = settings.vision_low_confidence
        self.high = settings.vision_high_confidence
        if not 0.0 <= self.low < self.high <= 1.0:
            raise ValueError(f"need 0 <= low < high <= 1, got low={self.low}, high={self.high}")
        self.allow_demo_sources = settings.allow_demo_sources

    def sources_ok(self, advisory: AdvisoryResult | None) -> bool:
        """Can this advisory back an answer? Verified and fresh sources always can. Demo sources (never
        verified) can only in dev/test, when ALLOW_DEMO_SOURCES is on, and never if stale."""
        if advisory is None or not advisory.sources:
            return False
        if advisory.usable:
            return True
        return self.allow_demo_sources and advisory.demo_only and not any(s.stale for s in advisory.sources)

    def band(self, confidence: float | None) -> ConfidenceBand | None:
        return None if confidence is None else BAND_OF_TIER[self.tier(confidence)]

    # 1. image quality
    def check_quality(self, q: QualityResult) -> PolicyDecision | None:
        if q.passed:
            return None
        tip = " ".join(QUALITY_TIPS[i] for i in q.issues[:2] if i in QUALITY_TIPS)
        return PolicyDecision(
            state=DecisionState.NEEDS_BETTER_IMAGE,
            reason=f"quality:{q.reason}",
            message=f"Please upload a clearer, well-lit close-up photo of a single affected leaf. {tip}".strip(),
        )

    # 2. crop
    def check_crop(self, crop: str) -> PolicyDecision | None:
        if crop.strip().lower() == "soybean":
            return None
        return PolicyDecision(
            state=DecisionState.UNSUPPORTED,
            reason="crop_not_soybean",
            message="KrishiMitra currently supports soybean only.",
        )

    # 3. intent: intents that end the run before any model is called
    def check_intent(self, i: IntentResult) -> PolicyDecision | None:
        if i.intent == Intent.EXPERT_ESCALATION:
            return PolicyDecision(
                state=DecisionState.EXPERT_REVIEW,
                reason="farmer_requested_expert",
                message="Your case is being sent to a human agriculture expert.",
            )
        if i.intent == Intent.UNSUPPORTED_REQUEST:
            return PolicyDecision(
                state=DecisionState.UNSUPPORTED,
                reason="unsupported_request",
                message="KrishiMitra currently helps with soybean crop health only. For other crops, loans, "
                "prices or schemes, please contact your local agriculture office.",
            )
        if i.intent != Intent.CROP_HEALTH_IMAGE and i.confidence < INTENT_MIN_CONFIDENCE:
            return PolicyDecision(
                state=DecisionState.NEEDS_MORE_CONTEXT,
                reason="intent_unclear",
                message="Please tell us a little more, or add a close-up photo of an affected leaf.",
                follow_up_question="What do you see on the plant, or what would you like to know?",
                follow_up=follow_up("describe_problem"),
            )
        return None

    # treatment_safety path: never a dose, only a pointer to a verified structured source, else escalate
    def decide_treatment(self, sources: AdvisoryResult | None) -> PolicyDecision:
        structured = [s for s in (sources.sources if sources else []) if s.verified and s.structured and not s.stale]
        if not structured:
            return PolicyDecision(
                state=DecisionState.EXPERT_REVIEW,
                reason="treatment_needs_expert",
                message=(
                    f"{NO_DOSE} We do not have a verified source for this, so your question is being sent "
                    "to a human agriculture expert. Meanwhile, contact your local Krishi Vigyan Kendra or "
                    "agriculture officer before spraying anything."
                ),
            )
        refs = "; ".join(f"{s.title} ({s.publisher})" for s in structured)
        return PolicyDecision(
            state=DecisionState.PRELIMINARY_GUIDANCE,
            reason="treatment_verified_source",
            message=(
                f"{NO_DOSE} Please refer to: {refs}. Always follow the product label and confirm with "
                "your agriculture officer before applying anything."
            ),
        )

    # weather_context path
    def decide_weather(self, weather: WeatherResult | None) -> PolicyDecision:
        if weather is None or not weather.usable:
            return self.decide_sources_missing("weather")
        return PolicyDecision(
            state=DecisionState.PRELIMINARY_GUIDANCE,
            reason="weather_context",
            message=(
                f"{weather.summary} Source: {weather.source_label}. Weather information is indicative; "
                "check local forecasts before field work."
            ),
        )

    # general_crop_question / advisory_lookup paths
    def decide_text_answer(self, intent: Intent, advisory: AdvisoryResult | None) -> PolicyDecision:
        if not self.sources_ok(advisory):
            return self.decide_sources_missing("advisory")
        demo = f" {DEMO_NOTE}" if advisory.demo_only else ""
        return PolicyDecision(
            state=DecisionState.PRELIMINARY_GUIDANCE,
            reason=intent.value,
            message=f"{advisory.summary}{demo} This is general information; confirm with your local agriculture officer.",
        )

    # 4-5-6. confidence tier
    def tier(self, confidence: float) -> Tier:
        if confidence < self.low:
            return Tier.LOW
        if confidence <= self.high:
            return Tier.MID
        return Tier.HIGH

    def pick_top(self, results: list[VisionResult]) -> VisionResult:
        return max(results, key=lambda r: r.confidence)

    # 7. conflicting models
    def models_conflict(self, results: list[VisionResult]) -> bool:
        return len({r.label for r in results}) > 1

    def decide_low(self, has_field_overview: bool) -> PolicyDecision:
        if not has_field_overview:
            return PolicyDecision(
                state=DecisionState.NEEDS_MORE_CONTEXT,
                reason="low_confidence_request_evidence",
                message="We cannot tell what this is from the photo. " + DISCLAIMER,
                follow_up_question="Can you add a photo of the wider field showing how the plants look?",
                follow_up=follow_up("field_overview_photo"),
            )
        return PolicyDecision(
            state=DecisionState.EXPERT_REVIEW,
            reason="low_confidence_escalate",
            message="We are not confident enough to say anything about this. Sending to a human expert.",
        )

    def decide_conflict(self) -> PolicyDecision:
        return PolicyDecision(
            state=DecisionState.EXPERT_REVIEW,
            reason="models_conflict",
            message="Our checks disagree with each other. Sending to a human expert.",
        )

    def decide_unknown_label(self) -> PolicyDecision:
        return PolicyDecision(
            state=DecisionState.EXPERT_REVIEW,
            reason="label_unknown",
            message="We could not match this to a known condition. Sending to a human expert.",
        )

    def decide_sources_missing(self, why: str) -> PolicyDecision:
        return PolicyDecision(
            state=DecisionState.EXPERT_REVIEW,
            reason=f"sources_unavailable:{why}",
            message="We do not have a verified source to support guidance here. Sending to a human expert.",
        )

    def decide_guidance(
        self,
        tier: Tier,
        label: Category,
        advisory: AdvisoryResult,
        weather: WeatherResult | None,
    ) -> PolicyDecision:
        demo = f" {DEMO_NOTE}" if advisory.demo_only else ""
        if tier == Tier.MID:
            return PolicyDecision(
                state=DecisionState.PRELIMINARY_GUIDANCE,
                reason="mid_confidence",
                message=(
                    f"The photo may show signs of {label.value.replace('_', ' ')}. {DISCLAIMER} "
                    f"{advisory.summary}{demo} No treatment is suggested at this confidence level."
                ),
                follow_up_question="Are the symptoms on older leaves, younger leaves, or both?",
                follow_up=follow_up("leaf_position"),
            )
        weather_note = f" {weather.summary} (Weather source: {weather.source_label}.)" if weather else ""
        return PolicyDecision(
            state=DecisionState.PRELIMINARY_GUIDANCE,
            reason="high_confidence",
            message=(
                f"The photo looks consistent with {label.value.replace('_', ' ')}. {DISCLAIMER} "
                f"{advisory.summary}{demo}{weather_note} Please confirm with your local agriculture officer "
                "before taking any action."
            ),
        )
