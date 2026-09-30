"""Keyword-rule intent classifier (cheap on purpose; no model call)."""

from app.schemas.orchestration import Intent, IntentResult

DIAGNOSIS_KEYWORDS = [
    "spot", "spots", "yellow", "rust", "disease", "leaf", "insect", "hole", "holes",
    "worm", "wilt", "pest", "brown", "curl",
    "डाग", "पिवळ", "रोग", "पान", "कीड", "अळी", "बुरशी",
]
ADVICE_KEYWORDS = ["advice", "what should", "how to", "help", "सल्ला", "काय करावे"]


class IntentRouter:
    model_name = "keyword-intent-rules"

    def classify(self, text: str) -> IntentResult:
        t = text.lower()
        diag = [k for k in DIAGNOSIS_KEYWORDS if k in t]
        if diag:
            return IntentResult(intent=Intent.DIAGNOSIS, matched=diag)
        advice = [k for k in ADVICE_KEYWORDS if k in t]
        if advice:
            return IntentResult(intent=Intent.GENERAL_ADVICE, matched=advice)
        return IntentResult(intent=Intent.UNKNOWN)
