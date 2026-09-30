"""Case storage. In-memory implementation; swap for a Supabase-backed one later.

The API only talks to the CaseStore interface, so persistence can change without touching routes.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from app.schemas.api import CaseCreate, CaseOut, ImageKind, ImageOut
from app.schemas.orchestration import OrchestratorResult


@dataclass
class StoredImage:
    meta: ImageOut
    data: bytes


class CaseStore(Protocol):
    def create_case(self, data: CaseCreate) -> CaseOut: ...
    def get_case(self, case_id: UUID) -> CaseOut | None: ...
    def put_image(self, case_id: UUID, kind: ImageKind, content_type: str, data: bytes) -> ImageOut: ...
    def get_image(self, case_id: UUID, kind: ImageKind) -> StoredImage | None: ...
    def save_result(self, case_id: UUID, result: OrchestratorResult) -> None: ...
    def get_result(self, case_id: UUID) -> OrchestratorResult | None: ...


class InMemoryCaseStore:
    def __init__(self) -> None:
        self._cases: dict[UUID, CaseOut] = {}
        self._images: dict[tuple[UUID, ImageKind], StoredImage] = {}
        self._results: dict[UUID, OrchestratorResult] = {}

    def create_case(self, data: CaseCreate) -> CaseOut:
        case = CaseOut(id=uuid4(), created_at=datetime.now(UTC), **data.model_dump())
        self._cases[case.id] = case
        return case

    def get_case(self, case_id: UUID) -> CaseOut | None:
        return self._cases.get(case_id)

    def put_image(self, case_id: UUID, kind: ImageKind, content_type: str, data: bytes) -> ImageOut:
        """One image per kind per case; a re-upload replaces the previous one."""
        meta = ImageOut(
            id=uuid4(),
            case_id=case_id,
            kind=kind,
            content_type=content_type,
            size_bytes=len(data),
            created_at=datetime.now(UTC),
        )
        self._images[(case_id, kind)] = StoredImage(meta=meta, data=data)
        return meta

    def get_image(self, case_id: UUID, kind: ImageKind) -> StoredImage | None:
        return self._images.get((case_id, kind))

    def save_result(self, case_id: UUID, result: OrchestratorResult) -> None:
        self._results[case_id] = result
        self._cases[case_id] = self._cases[case_id].model_copy(update={"decision_state": result.state})

    def get_result(self, case_id: UUID) -> OrchestratorResult | None:
        return self._results.get(case_id)
