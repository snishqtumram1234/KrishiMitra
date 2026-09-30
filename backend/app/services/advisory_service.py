"""PLACEHOLDER advisory retrieval. Replace with retrieval over data/advisories/ later.

Never returns treatment or dosage text. Treatment questions may only be answered by pointing to a
verified *structured* source; none exist yet, so treatment_sources() returns nothing and those
cases escalate to an expert.
"""

from app.schemas.case import Category
from app.schemas.orchestration import AdvisoryResult, AdvisorySource


class AdvisoryService:
    model_name = "placeholder-advisory"

    def retrieve(self, label: Category, district: str) -> AdvisoryResult:
        """Advisory for a (preliminary) image label."""
        return AdvisoryResult(
            sources=[
                AdvisorySource(
                    title=f"Placeholder advisory: {label.value}",
                    publisher="placeholder",
                    verified=True,
                )
            ],
            summary=f"General information about {label.value} symptoms in soybean ({district}).",
        )

    def search(self, query: str, district: str) -> AdvisoryResult:
        """Advisory for a text question (general crop questions and advisory lookups)."""
        return AdvisoryResult(
            sources=[AdvisorySource(title="Placeholder soybean advisory", publisher="placeholder", verified=True)],
            summary=f"General soybean guidance for {district}.",
        )

    def treatment_sources(self, query: str, district: str) -> AdvisoryResult:
        """Verified structured treatment records only. None loaded yet."""
        return AdvisoryResult(sources=[], summary="")
