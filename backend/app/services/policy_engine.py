"""Pure routing/safety policy (CLAUDE.md "Routing policy"). No I/O, no model calls.

Each check_* returns a terminal PolicyDecision, or None to continue.
No output of this module ever contains treatment or dosage advice.
"""

from app.config import Settings
from app.schemas.case import Category, DecisionState
from app.schemas.orchestration import (
    AdvisoryResult,
    Intent,
    IntentResult,
    PolicyDecision,
    QualityResult,
    Tier,
    VisionResult,
    WeatherResult,
)

DISCLAIMER = "This is a preliminary observation, not a confirmed diagnosis."

QUALITY_TIPS = {
    "missing_image": "No photo was received.",
    "unreadable_image": "The file could not be opened as a photo; please send a JPEG or PNG.",
    "too_small": "The photo is too small; move closer so the leaf fills most of the frame.",
    "too_dark": "The photo is too dark; take it in daylight.",
    "too_bright": "The photo is overexposed; avoid direct glare or shade the leaf.",
    "blurry": "The photo is blurry; hold the phone steady and tap the leaf to focus.",
}


class PolicyEngine:
    def __init__(self, settings: Settings):
        self.low = settings.vision_low_confidence
        self.high = settings.vision_high_confidence
        if not 0.0 <= self.low < self.high <= 1.0:
            raise ValueError(f"need 0 <= low < high <= 1, got low={self.low}, high={self.high}")

    # 1. image quality
    def check_quality(self, q: QualityResult) -> PolicyDecision | None:
        if q.passed:
            return None
        tip = QUALITY_TIPS.get(q.reason or "", "")
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

    # 3. intent
    def check_intent(self, i: IntentResult) -> PolicyDecision | None:
        if i.intent != Intent.UNKNOWN:
            return None
        return PolicyDecision(
            state=DecisionState.NEEDS_MORE_CONTEXT,
            reason="intent_unknown",
            message="Please describe what you see on the plant (for example spots, yellowing, holes).",
            follow_up_question="What symptoms do you see on the leaves?",
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
        if tier == Tier.MID:
            return PolicyDecision(
                state=DecisionState.PRELIMINARY_GUIDANCE,
                reason="mid_confidence",
                message=(
                    f"The photo may show signs of {label.value.replace('_', ' ')}. {DISCLAIMER} "
                    f"{advisory.summary} No treatment is suggested at this confidence level."
                ),
                follow_up_question="Are the symptoms on older leaves, younger leaves, or both?",
            )
        weather_note = f" {weather.summary}" if weather else ""
        return PolicyDecision(
            state=DecisionState.PRELIMINARY_GUIDANCE,
            reason="high_confidence",
            message=(
                f"The photo looks consistent with {label.value.replace('_', ' ')}. {DISCLAIMER} "
                f"{advisory.summary}{weather_note} Please confirm with your local agriculture officer "
                "before taking any action."
            ),
        )
