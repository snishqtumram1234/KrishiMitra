"""PLACEHOLDER advisory retrieval. Replace with retrieval over ingested advisory documents later.

Every source returned here is a DEMO source: verified=False, source_type="demo". Only a real ingested
advisory document may ever be verified=True (AdvisorySource refuses anything else). There is no ingestion
yet, so nothing here can be verified.

Never returns treatment or dosage text. Treatment questions may only be answered by pointing to a
verified *structured* source; none exist, so treatment_sources() returns nothing and those cases escalate.
"""

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

    def retrieve(self, label: Category, district: str) -> AdvisoryResult:
        """Advisory for a (preliminary) image label."""
        return AdvisoryResult(
            sources=[_demo_source(f"Demo advisory: {label.value}")],
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
