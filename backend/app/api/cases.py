from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.deps import get_orchestrator, get_store
from app.schemas.api import CaseCreate, CaseOut, ImageKind, ImageOut
from app.schemas.case import CaseInput
from app.schemas.orchestration import OrchestratorResult
from app.services.case_store import CaseStore
from app.services.orchestrator import Orchestrator

router = APIRouter(prefix="/cases", tags=["cases"])

MAX_IMAGE_BYTES = 10 * 1024 * 1024
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _case_or_404(store: CaseStore, case_id: UUID) -> CaseOut:
    case = store.get_case(case_id)
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")
    return case


@router.post("", response_model=CaseOut, status_code=status.HTTP_201_CREATED)
def create_case(body: CaseCreate, store: CaseStore = Depends(get_store)):
    return store.create_case(body)


@router.get("/{case_id}", response_model=CaseOut)
def get_case(case_id: UUID, store: CaseStore = Depends(get_store)):
    return _case_or_404(store, case_id)


@router.post("/{case_id}/images", response_model=ImageOut, status_code=status.HTTP_201_CREATED)
async def upload_image(
    case_id: UUID,
    kind: ImageKind,
    file: UploadFile = File(...),
    store: CaseStore = Depends(get_store),
):
    _case_or_404(store, case_id)
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Only JPEG, PNG or WebP images")
    data = await file.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Image larger than 10 MB")
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file")
    return store.put_image(case_id, kind, file.content_type, data)


@router.post("/{case_id}/analyze", response_model=OrchestratorResult)
def analyze_case(
    case_id: UUID,
    store: CaseStore = Depends(get_store),
    orchestrator: Orchestrator = Depends(get_orchestrator),
):
    case = _case_or_404(store, case_id)
    close_up = store.get_image(case_id, ImageKind.CLOSE_UP_LEAF)
    overview = store.get_image(case_id, ImageKind.FIELD_OVERVIEW)
    result = orchestrator.run(
        CaseInput(
            crop=case.crop,
            district=case.district,
            symptom_context=case.symptom_context,
            language=case.language,
            growth_stage=case.growth_stage,
            rainfall=case.rainfall,
            description=case.description,
            close_up_image=close_up.data if close_up else None,
            field_overview_image=overview.data if overview else None,
        )
    )
    store.save_result(case_id, result)
    return result


@router.get("/{case_id}/result", response_model=OrchestratorResult)
def get_result(case_id: UUID, store: CaseStore = Depends(get_store)):
    _case_or_404(store, case_id)
    result = store.get_result(case_id)
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case has not been analyzed yet")
    return result
