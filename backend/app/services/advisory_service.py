"""Advisory retrieval.

Two kinds of source:
  * INGESTED excerpts: verbatim, descriptive passages from real advisory documents, built by
    scripts/build_advisory_excerpts.py (ADVISORY_EXCERPTS_PATH). They carry the document's title, publisher, link and the
    PDF page. They are `verified` only if a human says so in verification.json (keyed by source_url); the default is False.
  * DEMO placeholders (verified=False, source_type="demo") for any label with no excerpt.

Never returns treatment or dosage text: the excerpt builder refuses doses, formulation codes and chemical names, and
treatment questions may only be answered by a verified *structured* source, none of which exist (treatment_sources()
returns nothing, so those cases escalate).
"""

import json
from pathlib import Path

from app.config import Settings, get_settings
from app.schemas.case import Category
from app.schemas.orchestration import AdvisoryResult, AdvisorySource

DEMO_PUBLISHER = "KrishiMitra demo data (not a real advisory)"


def _demo_source(title: str) -> AdvisorySource:
    return AdvisorySource(
        title=title,
        publisher=DEMO_PUBLISHER,
        verified=False,
        source_type="demo",
        published_at=None,
        source_url=None,
    )


# Words that tell us which condition a free-text question is about (English and Marathi). Used only to pick context passages.
TOPIC_WORDS = {
    "insect_damage": ("insect", "caterpillar", "larva", "semilooper", "eaten", "eating", "defoliat", "worm", "pests", "अळी", "कीड", "किडे", "कीटक"),
    "rust_like": ("rust", "pustule", "तांबेरा"),
    "yellow_mosaic": ("mosaic", "whitefly", "white fly", "मोझॅक"),
}


def topic_for_text(query: str) -> str | None:
    """The condition a question is about: the topic with the most matching words; a tie or no match means unknown."""
    q = (query or "").lower()
    scores = {topic: sum(w in q for w in words) for topic, words in TOPIC_WORDS.items()}
    best = max(scores.values(), default=0)
    winners = [t for t, n in scores.items() if n == best]
    return winners[0] if best > 0 and len(winners) == 1 else None


class AdvisoryService:
    model_name = "placeholder-advisory"
    _excerpts: list[dict] = []
    _verified: dict[str, bool] = {}

    def __init__(self, settings: Settings | None = None):
        settings = settings or get_settings()
        path = settings.advisory_excerpts_path
        if path:
            file = Path(path)
            self._excerpts = json.loads(file.read_text(encoding="utf-8"))
            ver = file.with_name("verification.json")
            if ver.exists():
                self._verified = {str(k): bool(v) for k, v in json.loads(ver.read_text(encoding="utf-8")).items()}
        if self._excerpts:
            self.model_name = "advisory-excerpts"

    def _ingested(self, topic: str, kinds: tuple[str, ...] = ("description",)) -> list[AdvisorySource]:
        return [
            AdvisorySource(
                title=e["title"],
                publisher=e["publisher"],
                verified=self._verified.get(e.get("source_url") or "", False),
                structured=False,
                source_type="ingested",
                published_at=e.get("published_at"),
                source_url=e.get("source_url"),
                excerpt=e["excerpt"],
                page=e.get("page"),
                excerpt_kind=e.get("kind", "description"),
            )
            for e in self._excerpts
            if e["topic"] == topic and e.get("kind", "description") in kinds
        ]

    def retrieve(self, label: Category, district: str) -> AdvisoryResult:
        """Advisory for a (preliminary) image label."""
        sources = self._ingested(label.value, ("description", "management")) or [_demo_source(f"Demo advisory: {label.value}")]
        return AdvisoryResult(
            sources=sources,
            summary=f"General information about {label.value} symptoms in soybean ({district}).",
        )

    def search(self, query: str, district: str) -> AdvisoryResult:
        """Advisory for a text question (general crop questions and advisory lookups)."""
        return AdvisoryResult(
            sources=[_demo_source("Demo soybean advisory")],
            summary=f"General soybean guidance for {district}.",
        )

    def treatment_sources(self, query: str, district: str) -> AdvisoryResult:
        """Verified structured treatment records only. None exist yet.

        For context, a treatment-style question also gets the descriptive passage and the NON-CHEMICAL good practices from the
        ingested documents when the question is about a condition we have text for. These are not structured treatment records,
        so the policy still sends the question to an expert; they only give the farmer something real to read meanwhile.
        """
        topic = topic_for_text(query)
        sources = self._ingested(topic, ("description", "management")) if topic else []
        return AdvisoryResult(sources=sources, summary="")
