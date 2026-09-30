"""PLACEHOLDER advisory retrieval. Replace with retrieval over data/advisories/ later.

Returns a stub source only; it never returns treatment or dosage text.
"""

from app.schemas.case import Category
from app.schemas.orchestration import AdvisoryResult, AdvisorySource


class AdvisoryService:
    model_name = "placeholder-advisory"

    def retrieve(self, label: Category, district: str) -> AdvisoryResult:
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
