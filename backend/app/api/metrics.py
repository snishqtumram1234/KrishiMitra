"""Orchestration metrics, computed live from routing_runs / model_runs.

Expert-only: these aggregate every farmer's cases (counts and timings, no personal data).
"""

from fastapi import APIRouter, Depends, Query

from app.api.auth import require_expert
from app.api.deps import get_store
from app.schemas.metrics import CostLatencyOut, Overview, RoutesOut
from app.services import metrics_service as m
from app.services.case_store import CaseStore

router = APIRouter(prefix="/api/metrics", tags=["metrics"], dependencies=[Depends(require_expert)])

Days = Query(None, ge=1, le=365, description="Only include analyses from the last N days (default: all time)")


def _load(store: CaseStore, days: int | None):
    window = m.make_window(days)
    runs, models = store.list_runs(window.since)
    return runs, models, window


@router.get("/overview", response_model=Overview)
def metrics_overview(days: int | None = Days, store: CaseStore = Depends(get_store)):
    return m.overview(*_load(store, days))


@router.get("/routes", response_model=RoutesOut)
def metrics_routes(days: int | None = Days, store: CaseStore = Depends(get_store)):
    return m.routes(*_load(store, days))


@router.get("/cost-latency", response_model=CostLatencyOut)
def metrics_cost_latency(days: int | None = Days, store: CaseStore = Depends(get_store)):
    return m.cost_latency(*_load(store, days))
