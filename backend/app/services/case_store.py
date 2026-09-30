"""Case storage interface + in-memory implementation (dev/tests).

SupabaseCaseStore (supabase_store.py) implements the same interface against Postgres + Storage.
Ownership is enforced by the API layer (case.user_id == caller), not here.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from app.schemas.api import CaseCreate, CaseOut, ImageKind, ImageOut
from app.schemas.expert import AuditEvent, ExpertReviewRecord, ExpertStatus, FollowUpRecord
from app.schemas.runs import ModelRunRecord, RoutingRunRecord, WeatherSnapshotRecord

EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


def storage_path(user_id: UUID, case_id: UUID, kind: ImageKind, image_id: UUID, content_type: str) -> str:
    """<user_id>/<case_id>/<kind>-<image_id>.<ext>; the first folder is what storage RLS checks."""
    return f"{user_id}/{case_id}/{kind.value}-{image_id}.{EXTENSIONS.get(content_type, 'bin')}"


@dataclass
class StoredImage:
    meta: ImageOut
    data: bytes


class CaseStore(Protocol):
    def create_case(self, user_id: UUID, data: CaseCreate) -> CaseOut: ...
    def get_case(self, case_id: UUID) -> CaseOut | None: ...
    def list_cases(self, user_id: UUID) -> list[CaseOut]: ...
    def put_image(self, case: CaseOut, kind: ImageKind, content_type: str, data: bytes) -> ImageOut: ...
    def get_image(self, case_id: UUID, kind: ImageKind) -> StoredImage | None: ...
    def save_analysis(self, run: RoutingRunRecord, models: list[ModelRunRecord]) -> None: ...
    def get_latest_run(self, case_id: UUID) -> RoutingRunRecord | None: ...
    def get_run(self, run_id: UUID) -> tuple[RoutingRunRecord, list[ModelRunRecord]] | None: ...
    def save_weather_snapshot(self, snap: WeatherSnapshotRecord) -> None: ...
    def latest_live_weather(self, district: str) -> WeatherSnapshotRecord | None: ...
    def list_images(self, case_id: UUID) -> list[ImageOut]: ...
    def save_expert_review(self, rec: ExpertReviewRecord) -> None: ...
    def update_expert_review(self, rec: ExpertReviewRecord) -> None: ...
    def list_expert_reviews(
        self, case_id: UUID | None = None, statuses: set[ExpertStatus] | None = None
    ) -> list[ExpertReviewRecord]: ...
    def add_follow_up(self, rec: FollowUpRecord) -> None: ...
    def list_follow_ups(self, case_id: UUID) -> list[FollowUpRecord]: ...
    def save_audit_event(self, ev: AuditEvent) -> None: ...
    def list_audit_events(self, case_id: UUID | None = None) -> list[AuditEvent]: ...


class InMemoryCaseStore:
    def __init__(self) -> None:
        self._cases: dict[UUID, CaseOut] = {}
        self._images: list[StoredImage] = []  # append-only, latest per kind wins
        self._runs: list[RoutingRunRecord] = []
        self._model_runs: list[ModelRunRecord] = []
        self._weather: list[WeatherSnapshotRecord] = []
        self._expert: dict[UUID, ExpertReviewRecord] = {}
        self._follow_ups: list[FollowUpRecord] = []
        self._audit: list[AuditEvent] = []

    def create_case(self, user_id: UUID, data: CaseCreate) -> CaseOut:
        case = CaseOut(id=uuid4(), user_id=user_id, created_at=datetime.now(UTC), **data.model_dump())
        self._cases[case.id] = case
        return case

    def get_case(self, case_id: UUID) -> CaseOut | None:
        return self._cases.get(case_id)

    def list_cases(self, user_id: UUID) -> list[CaseOut]:
        mine = [c for c in self._cases.values() if c.user_id == user_id]
        return sorted(mine, key=lambda c: c.created_at, reverse=True)

    def put_image(self, case: CaseOut, kind: ImageKind, content_type: str, data: bytes) -> ImageOut:
        image_id = uuid4()
        meta = ImageOut(
            id=image_id,
            case_id=case.id,
            kind=kind,
            storage_path=storage_path(case.user_id, case.id, kind, image_id, content_type),
            content_type=content_type,
            size_bytes=len(data),
            created_at=datetime.now(UTC),
        )
        self._images.append(StoredImage(meta=meta, data=data))
        return meta

    def get_image(self, case_id: UUID, kind: ImageKind) -> StoredImage | None:
        matches = [i for i in self._images if i.meta.case_id == case_id and i.meta.kind == kind]
        return matches[-1] if matches else None

    def save_analysis(self, run: RoutingRunRecord, models: list[ModelRunRecord]) -> None:
        self._runs.append(run)
        self._model_runs.extend(models)
        case = self._cases[run.case_id]
        self._cases[run.case_id] = case.model_copy(update={"decision_state": run.decision_state})

    def get_latest_run(self, case_id: UUID) -> RoutingRunRecord | None:
        runs = [r for r in self._runs if r.case_id == case_id]
        return runs[-1] if runs else None

    def get_run(self, run_id: UUID) -> tuple[RoutingRunRecord, list[ModelRunRecord]] | None:
        run = next((r for r in self._runs if r.id == run_id), None)
        if run is None:
            return None
        return run, [m for m in self._model_runs if m.routing_run_id == run_id]

    def save_weather_snapshot(self, snap: WeatherSnapshotRecord) -> None:
        self._weather.append(snap)

    def latest_live_weather(self, district: str) -> WeatherSnapshotRecord | None:
        live = [w for w in self._weather if w.district == district and w.source == "live"]
        return max(live, key=lambda w: w.observed_at, default=None)

    def list_images(self, case_id: UUID) -> list[ImageOut]:
        return [i.meta for i in self._images if i.meta.case_id == case_id]

    def save_expert_review(self, rec: ExpertReviewRecord) -> None:
        self._expert[rec.id] = rec

    def update_expert_review(self, rec: ExpertReviewRecord) -> None:
        self._expert[rec.id] = rec

    def list_expert_reviews(
        self, case_id: UUID | None = None, statuses: set[ExpertStatus] | None = None
    ) -> list[ExpertReviewRecord]:
        rows = [r for r in self._expert.values()
                if (case_id is None or r.case_id == case_id) and (statuses is None or r.status in statuses)]
        return sorted(rows, key=lambda r: r.created_at, reverse=True)

    def add_follow_up(self, rec: FollowUpRecord) -> None:
        self._follow_ups.append(rec)

    def list_follow_ups(self, case_id: UUID) -> list[FollowUpRecord]:
        return [f for f in self._follow_ups if f.case_id == case_id]

    def save_audit_event(self, ev: AuditEvent) -> None:
        self._audit.append(ev)

    def list_audit_events(self, case_id: UUID | None = None) -> list[AuditEvent]:
        return [e for e in self._audit if case_id is None or e.case_id == case_id]
