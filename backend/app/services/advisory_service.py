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

    def _ingested(self, topic: str) -> list[AdvisorySource]:
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
            )
            for e in self._excerpts
            if e["topic"] == topic
        ]

    def retrieve(self, label: Category, district: str) -> AdvisoryResult:
        """Advisory for a (preliminary) image label."""
        sources = self._ingested(label.value) or [_demo_source(f"Demo advisory: {label.value}")]
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
        """Verified structured treatment records only. None exist yet."""
        return AdvisoryResult(sources=[], summary="")
