"""CaseStore backed by Supabase: Postgres via PostgREST, images in the private `case-images` bucket.

Uses the service-role key (bypasses RLS), so every read is scoped by the API layer's ownership
check. Never expose this key to the frontend.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx

from app.schemas.api import CaseCreate, CaseOut, ImageKind, ImageOut
from app.schemas.expert import AuditEvent, ExpertReviewRecord, ExpertStatus, FollowUpRecord
from app.schemas.runs import ModelRunRecord, RoutingRunRecord, WeatherSnapshotRecord
from app.services.case_store import StoredImage, storage_path

BUCKET = "case-images"
CASE_COLUMNS = (
    "id,user_id,crop,district,symptom_context,language,growth_stage,symptom_started_at,"
    "recent_rainfall,description,entry_point,decision_state,created_at"
)


class SupabaseCaseStore:
    def __init__(self, url: str, service_key: str, client: httpx.Client | None = None):
        if not url or not service_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY are required for STORE_BACKEND=supabase")
        self._http = client or httpx.Client(timeout=30)
        self._base = url.rstrip("/")
        self._rest = f"{url.rstrip('/')}/rest/v1"
        self._storage = f"{url.rstrip('/')}/storage/v1/object/{BUCKET}"
        self._headers = {"apikey": service_key, "Authorization": f"Bearer {service_key}"}

    # ---------------------------------------------------------------- helpers
    def _select(self, table: str, params: dict) -> list[dict]:
        r = self._http.get(f"{self._rest}/{table}", params=params, headers=self._headers)
        r.raise_for_status()
        return r.json()

    def _select_all(self, table: str, params: dict, page: int = 1000) -> list[dict]:
        """PostgREST returns at most ~1000 rows per request; page through with limit/offset."""
        out: list[dict] = []
        while True:
            rows = self._select(table, {**params, "limit": str(page), "offset": str(len(out))})
            out += rows
            if len(rows) < page:
                return out

    def _insert(self, table: str, rows: dict | list[dict]) -> list[dict]:
        r = self._http.post(
            f"{self._rest}/{table}",
            json=rows,
            headers={**self._headers, "Prefer": "return=representation"},
        )
        r.raise_for_status()
        return r.json()

    def _update(self, table: str, row_id: UUID, values: dict) -> None:
        r = self._http.patch(f"{self._rest}/{table}", params={"id": f"eq.{row_id}"}, json=values,
                             headers=self._headers)
        r.raise_for_status()

    # ---------------------------------------------------------------- cases
    def create_case(self, user_id: UUID, data: CaseCreate, entry_point: str = "crop_check") -> CaseOut:
        row = {"user_id": str(user_id), "entry_point": entry_point, **data.model_dump(mode="json")}
        return CaseOut(**self._insert("crop_cases", row)[0])

    def get_case(self, case_id: UUID) -> CaseOut | None:
        rows = self._select("crop_cases", {"id": f"eq.{case_id}", "select": CASE_COLUMNS})
        return CaseOut(**rows[0]) if rows else None

    def list_cases(self, user_id: UUID) -> list[CaseOut]:
        rows = self._select(
            "crop_cases", {"user_id": f"eq.{user_id}", "select": CASE_COLUMNS, "order": "created_at.desc"}
        )
        return [CaseOut(**r) for r in rows]

    # ---------------------------------------------------------------- images
    def put_image(self, case: CaseOut, kind: ImageKind, content_type: str, data: bytes) -> ImageOut:
        image_id = uuid4()
        path = storage_path(case.user_id, case.id, kind, image_id, content_type)
        r = self._http.post(
            f"{self._storage}/{path}",
            content=data,
            headers={**self._headers, "Content-Type": content_type, "x-upsert": "false"},
        )
        r.raise_for_status()
        row = self._insert("case_images", {
            "id": str(image_id),
            "case_id": str(case.id),
            "kind": kind.value,
            "storage_path": path,
            "content_type": content_type,
            "size_bytes": len(data),
        })[0]
        return ImageOut(**row)

    def get_image(self, case_id: UUID, kind: ImageKind) -> StoredImage | None:
        rows = self._select("case_images", {
            "case_id": f"eq.{case_id}",
            "kind": f"eq.{kind.value}",
            "order": "created_at.desc",
            "limit": "1",
            "select": "id,case_id,kind,storage_path,content_type,size_bytes,created_at",
        })
        if not rows:
            return None
        meta = ImageOut(**rows[0])
        r = self._http.get(f"{self._storage}/{meta.storage_path}", headers=self._headers)
        r.raise_for_status()
        return StoredImage(meta=meta, data=r.content)

    # ---------------------------------------------------------------- runs
    def save_analysis(self, run: RoutingRunRecord, models: list[ModelRunRecord]) -> None:
        self._insert("routing_runs", run.model_dump(mode="json"))
        if models:
            self._insert("model_runs", [m.model_dump(mode="json") for m in models])
        r = self._http.patch(
            f"{self._rest}/crop_cases",
            params={"id": f"eq.{run.case_id}"},
            json={"decision_state": run.decision_state.value if run.decision_state else None,
                  "updated_at": datetime.now(UTC).isoformat()},
            headers=self._headers,
        )
        r.raise_for_status()

    def get_latest_run(self, case_id: UUID) -> RoutingRunRecord | None:
        rows = self._select("routing_runs", {"case_id": f"eq.{case_id}", "order": "created_at.desc", "limit": "1"})
        return RoutingRunRecord(**rows[0]) if rows else None

    def get_run(self, run_id: UUID) -> tuple[RoutingRunRecord, list[ModelRunRecord]] | None:
        rows = self._select("routing_runs", {"id": f"eq.{run_id}"})
        if not rows:
            return None
        models = self._select("model_runs", {"routing_run_id": f"eq.{run_id}", "order": "created_at.asc"})
        return RoutingRunRecord(**rows[0]), [ModelRunRecord(**m) for m in models]

    # ---------------------------------------------------------------- weather
    def save_weather_snapshot(self, snap: WeatherSnapshotRecord) -> None:
        self._insert("weather_snapshots", snap.model_dump(mode="json"))

    def latest_live_weather(self, district: str) -> WeatherSnapshotRecord | None:
        rows = self._select("weather_snapshots", {
            "district": f"eq.{district}", "source": "eq.live", "order": "observed_at.desc", "limit": "1",
        })
        return WeatherSnapshotRecord(**rows[0]) if rows else None

    # ---------------------------------------------------------------- expert workflow
    IMAGE_COLUMNS = "id,case_id,kind,storage_path,content_type,size_bytes,created_at"

    def list_images(self, case_id: UUID) -> list[ImageOut]:
        rows = self._select("case_images", {"case_id": f"eq.{case_id}", "order": "created_at.asc",
                                            "select": self.IMAGE_COLUMNS})
        return [ImageOut(**r) for r in rows]

    def save_expert_review(self, rec: ExpertReviewRecord) -> None:
        self._insert("expert_reviews", rec.model_dump(mode="json"))

    def update_expert_review(self, rec: ExpertReviewRecord) -> None:
        self._update("expert_reviews", rec.id, rec.model_dump(mode="json", exclude={"id", "case_id", "created_at"}))

    def list_expert_reviews(
        self, case_id: UUID | None = None, statuses: set[ExpertStatus] | None = None
    ) -> list[ExpertReviewRecord]:
        params = {"order": "created_at.desc"}
        if case_id:
            params["case_id"] = f"eq.{case_id}"
        if statuses:
            params["status"] = f"in.({','.join(sorted(s.value for s in statuses))})"
        return [ExpertReviewRecord(**r) for r in self._select("expert_reviews", params)]

    def add_follow_up(self, rec: FollowUpRecord) -> None:
        self._insert("case_follow_ups", rec.model_dump(mode="json"))

    def list_follow_ups(self, case_id: UUID) -> list[FollowUpRecord]:
        rows = self._select("case_follow_ups", {"case_id": f"eq.{case_id}", "order": "created_at.asc"})
        return [FollowUpRecord(**r) for r in rows]

    def save_audit_event(self, ev: AuditEvent) -> None:
        self._insert("audit_events", ev.model_dump(mode="json"))

    def list_audit_events(self, case_id: UUID | None = None) -> list[AuditEvent]:
        params = {"order": "created_at.asc"} | ({"case_id": f"eq.{case_id}"} if case_id else {})
        return [AuditEvent(**r) for r in self._select("audit_events", params)]

    # ---------------------------------------------------------------- metrics
    def list_runs(self, since: datetime | None = None) -> tuple[list[RoutingRunRecord], list[ModelRunRecord]]:
        params = {"order": "created_at.asc"} | ({"created_at": f"gte.{since.isoformat()}"} if since else {})
        runs = [RoutingRunRecord(**r) for r in self._select_all("routing_runs", params)]
        models = [ModelRunRecord(**m) for m in self._select_all("model_runs", params)]
        return runs, models

    def list_images_for_cases(self, case_ids: list[UUID]) -> dict[UUID, list[ImageOut]]:
        out: dict[UUID, list[ImageOut]] = {cid: [] for cid in case_ids}
        for start in range(0, len(case_ids), 50):  # keep the request URL short
            chunk = case_ids[start:start + 50]
            rows = self._select("case_images", {
                "case_id": f"in.({','.join(str(c) for c in chunk)})", "order": "created_at.asc",
                "select": self.IMAGE_COLUMNS,
            })
            for r in rows:
                img = ImageOut(**r)
                out[img.case_id].append(img)
        return out

    def get_image_meta(self, image_id: UUID) -> ImageOut | None:
        rows = self._select("case_images", {"id": f"eq.{image_id}", "select": self.IMAGE_COLUMNS})
        return ImageOut(**rows[0]) if rows else None

    def signed_image_url(self, image: ImageOut, expires_in: int, base_url: str | None = None) -> str:
        """Ask Supabase Storage to sign a download link for this private object."""
        r = self._http.post(f"{self._base}/storage/v1/object/sign/{BUCKET}/{image.storage_path}",
                            json={"expiresIn": expires_in}, headers=self._headers)
        r.raise_for_status()
        signed = r.json()["signedURL"]  # e.g. "/object/sign/case-images/<path>?token=..."
        return f"{self._base}/storage/v1{signed}" if signed.startswith("/") else signed
