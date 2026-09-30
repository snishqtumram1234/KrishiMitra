import io
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from PIL import Image

from app.api.auth import AuthUser, get_current_user
from app.api.deps import get_orchestrator, get_store
from app.schemas.api import AnalysisOut, CaseCreate, CaseOut, ImageKind, ImageOut, RunStep, RunTrace
from app.schemas.expert import ExpertFeedback
from app.schemas.orchestration import OrchestratorResult
from app.schemas.runs import RoutingRunRecord
from app.services.case_store import CaseStore
from app.services.expert_service import ExpertService
from app.services.orchestrator import Orchestrator, orchestrate_case

# Every route in this module requires a valid Supabase JWT.
cases = APIRouter(prefix="/api/cases", tags=["cases"], dependencies=[Depends(get_current_user)])
runs = APIRouter(prefix="/api/runs", tags=["runs"], dependencies=[Depends(get_current_user)])

MAX_IMAGE_BYTES = 10 * 1024 * 1024
FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}


def _owned_case(store: CaseStore, case_id: UUID, user: AuthUser) -> CaseOut:
    """404 (not 403) for other users' cases, so case IDs can't be probed."""
    case = store.get_case(case_id)
    if case is None or case.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")
    return case


def _sniff_image(data: bytes) -> str:
    """Return the real content type from the file bytes; reject anything that isn't an image."""
    try:
        with Image.open(io.BytesIO(data)) as im:
            fmt = im.format
            im.verify()
    except Exception:  # noqa: BLE001 - any decode failure (incl. decompression bombs) is a bad upload
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "File is not a valid JPEG, PNG or WebP image")
    if fmt not in FORMATS:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Only JPEG, PNG or WebP images")
    return FORMATS[fmt]


async def _read_image(file: UploadFile) -> tuple[bytes, str]:
    """Size and format checks shared by image upload and follow-up."""
    data = await file.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Image larger than 10 MB")
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file")
    return data, _sniff_image(data)  # trust the bytes, not the client's Content-Type


class CaseAnalysisOut(AnalysisOut):
    expert: ExpertFeedback | None = None  # latest expert-side status, review, or request for more info


def _analysis(run: RoutingRunRecord, store: CaseStore) -> CaseAnalysisOut:
    return CaseAnalysisOut(
        routing_run_id=run.id,
        case_id=run.case_id,
        state=run.decision_state,
        result=OrchestratorResult(**run.details["result"]),
        created_at=run.created_at,
        expert=ExpertService(store).feedback(run.case_id),
    )


@cases.post("", response_model=CaseOut, status_code=status.HTTP_201_CREATED)
def create_case(
    body: CaseCreate,
    user: AuthUser = Depends(get_current_user),
    store: CaseStore = Depends(get_store),
):
    return store.create_case(user.id, body)


@cases.get("", response_model=list[CaseOut])
def list_cases(user: AuthUser = Depends(get_current_user), store: CaseStore = Depends(get_store)):
    return store.list_cases(user.id)


@cases.get("/{case_id}", response_model=CaseOut)
def get_case(case_id: UUID, user: AuthUser = Depends(get_current_user), store: CaseStore = Depends(get_store)):
    return _owned_case(store, case_id, user)


@cases.post("/{case_id}/images", response_model=ImageOut, status_code=status.HTTP_201_CREATED)
async def upload_image(
    case_id: UUID,
    kind: ImageKind = Form(...),
    file: UploadFile = File(...),
    user: AuthUser = Depends(get_current_user),
    store: CaseStore = Depends(get_store),
):
    case = _owned_case(store, case_id, user)
    data, content_type = await _read_image(file)
    return store.put_image(case, kind, content_type, data)


@cases.post("/{case_id}/analyze", response_model=CaseAnalysisOut)
def analyze_case(
    case_id: UUID,
    user: AuthUser = Depends(get_current_user),
    store: CaseStore = Depends(get_store),
    orchestrator: Orchestrator = Depends(get_orchestrator),
):
    _owned_case(store, case_id, user)
    run, _ = orchestrate_case(case_id, store, orchestrator)
    return _analysis(run, store)


@cases.post("/{case_id}/follow-up", response_model=CaseAnalysisOut)
async def follow_up(
    case_id: UUID,
    answer: str | None = Form(None, max_length=2000),
    kind: ImageKind = Form(ImageKind.LEAF_CLOSEUP),
    file: UploadFile | None = File(None),
    user: AuthUser = Depends(get_current_user),
    store: CaseStore = Depends(get_store),
    orchestrator: Orchestrator = Depends(get_orchestrator),
):
    """Farmer answers a question and/or adds a photo; the orchestrator re-runs on the updated case."""
    case = _owned_case(store, case_id, user)
    answer = (answer or "").strip() or None
    if answer is None and file is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Send an answer, an image, or both")
    image = None
    if file is not None:
        data, content_type = await _read_image(file)
        image = store.put_image(case, kind, content_type, data)
    ExpertService(store).record_follow_up(case, user.id, answer, image.id if image else None)
    run, _ = orchestrate_case(case_id, store, orchestrator)
    return _analysis(run, store)


@cases.get("/{case_id}/analysis", response_model=CaseAnalysisOut)
def latest_analysis(case_id: UUID, user: AuthUser = Depends(get_current_user), store: CaseStore = Depends(get_store)):
    _owned_case(store, case_id, user)
    run = store.get_latest_run(case_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case has not been analyzed yet")
    return _analysis(run, store)


@runs.get("/{routing_run_id}", response_model=RunTrace)
def get_run(routing_run_id: UUID, user: AuthUser = Depends(get_current_user), store: CaseStore = Depends(get_store)):
    found = store.get_run(routing_run_id)
    if found is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found")
    run, model_runs = found
    case = store.get_case(run.case_id)
    if case is None or case.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found")
    result = run.details["result"]
    return RunTrace(
        routing_run_id=run.id,
        case_id=run.case_id,
        decision_state=run.decision_state,
        reason=run.reason,
        intent=run.intent,
        intent_confidence=result.get("intent_confidence"),
        intent_rule=result.get("intent_rule"),
        path=run.route,
        route_trace=result["route_trace"],
        steps=[
            RunStep(
                step=m.step,
                model_name=m.model_name,
                latency_ms=m.latency_ms,
                cost_usd=m.cost_usd,
                confidence=m.confidence,
                predicted_label=m.predicted_label,
                outcome=m.outcome,
                error=m.error,
            )
            for m in sorted(model_runs, key=lambda m: m.created_at)
        ],
        skipped_steps=result.get("skipped_steps", []),
        estimated_cost_saved_usd=result.get("estimated_cost_saved_usd", 0.0),
        total_latency_ms=run.latency_ms,
        total_cost_usd=run.cost_usd,
        created_at=run.created_at,
    )
