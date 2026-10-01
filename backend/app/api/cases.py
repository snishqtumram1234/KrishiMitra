import io
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from PIL import Image

from app.api.auth import AuthUser, get_current_user
from app.api.deps import get_orchestrator, get_store
from app.schemas.api import (
    AnalysisOut,
    CaseCreate,
    CaseOut,
    ImageKind,
    ImageOut,
    QuestionCreate,
    RunStep,
    RunTrace,
    SignedUrlOut,
)
from app.schemas.expert import ExpertFeedback
from app.schemas.orchestration import (
    ConfidenceBand,
    FollowUpOptions,
    OrchestratorResult,
    ReasonCode,
    TraceStep,
)
from app.schemas.runs import RoutingRunRecord
from app.services.case_store import CaseStore
from app.services.expert_service import ExpertService
from app.services.explain import OPTION_TEXT, split_reason, validate_follow_up_choice
from app.services.orchestrator import Orchestrator, orchestrate_case
from app.services.signed_urls import SIGNED_URL_TTL_SECONDS

# Every route in this module requires a valid Supabase JWT.
cases = APIRouter(prefix="/api/cases", tags=["cases"], dependencies=[Depends(get_current_user)])
questions = APIRouter(prefix="/api/questions", tags=["questions"], dependencies=[Depends(get_current_user)])
runs = APIRouter(prefix="/api/runs", tags=["runs"], dependencies=[Depends(get_current_user)])

MAX_IMAGE_BYTES = 10 * 1024 * 1024
FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}


def _owned_case(store: CaseStore, case_id: UUID, user: AuthUser) -> CaseOut:
    """404 (not 403) for other users' cases, so case IDs can't be probed."""
    case = store.get_case(case_id)
    if case is None or case.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")
    return case


def _with_images(store: CaseStore, found: list[CaseOut]) -> list[CaseOut]:
    """Attach every photo (with its id) to each case. One batched lookup, not one per case."""
    by_case = store.list_images_for_cases([c.id for c in found])
    return [c.model_copy(update={"images": by_case.get(c.id, [])}) for c in found]


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
    """POST /analyze, POST /follow-up, POST /api/questions and GET /analysis.

    The structured fields below mirror `result.*` so a client can read them at the top level."""

    expert: ExpertFeedback | None = None  # latest expert-side status, review, or request for more info
    reason_code: ReasonCode | None = None
    reason_detail: str | None = None
    confidence_band: ConfidenceBand | None = None
    missing_information: list[str] = []
    follow_up_options: FollowUpOptions | None = None
    trace: list[TraceStep] = []  # the full recorded run, for the client to replay


def _analysis(run: RoutingRunRecord, store: CaseStore) -> CaseAnalysisOut:
    result = OrchestratorResult(**run.details["result"])
    code, detail = (result.reason_code, result.reason_detail) if result.reason_code else split_reason(result.reason)
    return CaseAnalysisOut(
        routing_run_id=run.id,
        case_id=run.case_id,
        state=run.decision_state,
        result=result,
        created_at=run.created_at,
        expert=ExpertService(store).feedback(run.case_id),
        reason_code=code,
        reason_detail=detail,
        confidence_band=result.confidence_band,
        missing_information=result.missing_information,
        follow_up_options=result.follow_up_options,
        trace=result.trace,
    )


# ---------------------------------------------------------------- cases
@cases.post("", response_model=CaseOut, status_code=status.HTTP_201_CREATED)
def create_case(
    body: CaseCreate,
    user: AuthUser = Depends(get_current_user),
    store: CaseStore = Depends(get_store),
):
    return store.create_case(user.id, body)


@cases.get("", response_model=list[CaseOut])
def list_cases(user: AuthUser = Depends(get_current_user), store: CaseStore = Depends(get_store)):
    return _with_images(store, store.list_cases(user.id))


@cases.get("/{case_id}", response_model=CaseOut)
def get_case(case_id: UUID, user: AuthUser = Depends(get_current_user), store: CaseStore = Depends(get_store)):
    return _with_images(store, [_owned_case(store, case_id, user)])[0]


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


@cases.get("/{case_id}/images/{image_id}/signed-url", response_model=SignedUrlOut)
def image_signed_url(
    request: Request,
    case_id: UUID,
    image_id: UUID,
    user: AuthUser = Depends(get_current_user),
    store: CaseStore = Depends(get_store),
):
    """A 5-minute link to one private photo. Allowed for the case owner and for experts on escalated cases.
    Anyone else gets 404, the same as for an image that does not exist."""
    case = store.get_case(case_id)
    image = store.get_image_meta(image_id)
    if case is None or image is None or image.case_id != case_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Image not found")
    is_owner = case.user_id == user.id
    if not is_owner and not (user.is_expert and store.list_expert_reviews(case_id)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Image not found")

    url = store.signed_image_url(image, SIGNED_URL_TTL_SECONDS, base_url=str(request.base_url))
    if not is_owner:  # an expert looked at a farmer's photo: leave a trace
        ExpertService(store).audit("image_signed_url_issued", "expert", case_id, actor_id=user.id,
                                   image_id=str(image_id), image_kind=image.kind.value)
    return SignedUrlOut(
        image_id=image.id,
        case_id=case_id,
        kind=image.kind,
        content_type=image.content_type,
        url=url,
        expires_in=SIGNED_URL_TTL_SECONDS,
        expires_at=datetime.now(UTC) + timedelta(seconds=SIGNED_URL_TTL_SECONDS),
    )


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
    question_id: str | None = Form(None, max_length=50),
    option: str | None = Form(None, max_length=50),
    kind: ImageKind = Form(ImageKind.LEAF_CLOSEUP),
    file: UploadFile | None = File(None),
    user: AuthUser = Depends(get_current_user),
    store: CaseStore = Depends(get_store),
    orchestrator: Orchestrator = Depends(get_orchestrator),
):
    """Farmer answers a question and/or adds a photo; the orchestrator re-runs on the updated case.

    To answer a structured question from `follow_up_options`, send its `question_id` and, for choice
    questions, the chosen `option` code."""
    case = _owned_case(store, case_id, user)
    answer = (answer or "").strip() or None
    if problem := validate_follow_up_choice(question_id, option):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, problem)
    if answer is None and file is None and option is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Send an answer, an option, an image, or a mix")
    if answer is None and option is not None:
        answer = OPTION_TEXT.get((question_id, option))  # stored text so experts and the router can read it
    image = None
    if file is not None:
        data, content_type = await _read_image(file)
        image = store.put_image(case, kind, content_type, data)
    ExpertService(store).record_follow_up(case, user.id, answer, image.id if image else None,
                                          question_id=question_id, option=option)
    run, _ = orchestrate_case(case_id, store, orchestrator)
    return _analysis(run, store)


@cases.get("/{case_id}/analysis", response_model=CaseAnalysisOut)
def latest_analysis(case_id: UUID, user: AuthUser = Depends(get_current_user), store: CaseStore = Depends(get_store)):
    _owned_case(store, case_id, user)
    run = store.get_latest_run(case_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case has not been analyzed yet")
    return _analysis(run, store)


# ---------------------------------------------------------------- questions (no photo)
@questions.post("", response_model=CaseAnalysisOut, status_code=status.HTTP_201_CREATED)
def ask_question(
    body: QuestionCreate,
    user: AuthUser = Depends(get_current_user),
    store: CaseStore = Depends(get_store),
    orchestrator: Orchestrator = Depends(get_orchestrator),
):
    """Ask a text question with no photo. Creates a case (entry_point "question") and analyses it in one call.

    The intent router decides what happens: weather, advisory, treatment-safety, expert and general questions
    are answered without a photo. A crop-health question needs a photo, so it returns NEEDS_BETTER_IMAGE with
    missing_information ["close_up_photo"]; upload a photo to the returned case_id and analyse again."""
    case = store.create_case(
        user.id,
        CaseCreate(crop="soybean", district=body.district, symptom_context=body.question, language=body.language),
        entry_point="question",
    )
    run, _ = orchestrate_case(case.id, store, orchestrator)
    return _analysis(run, store)


# ---------------------------------------------------------------- runs
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
    code, detail = split_reason(run.reason) if run.reason else (None, None)
    return RunTrace(
        routing_run_id=run.id,
        case_id=run.case_id,
        decision_state=run.decision_state,
        reason=run.reason,
        reason_code=code,
        reason_detail=detail,
        confidence_band=result.get("confidence_band"),
        intent=run.intent,
        intent_confidence=result.get("intent_confidence"),
        intent_rule=result.get("intent_rule"),
        path=run.route,
        route_trace=result["route_trace"],
        trace=result.get("trace", []),
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
