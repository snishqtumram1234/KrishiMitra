"""The orchestrator: decides per query which step to run next and logs every call.

Flow: quality -> crop -> intent -> vision -> (by confidence tier) advisory [+ weather] -> decision.
"""

import time
from collections.abc import Callable
from typing import TypeVar
from uuid import UUID

from pydantic import BaseModel

from app.config import Settings, get_settings
from app.schemas.api import ImageKind
from app.schemas.case import Category, CaseInput
from app.schemas.orchestration import (
    AdvisoryResult,
    CallLog,
    OrchestratorResult,
    PolicyDecision,
    Tier,
    VisionResult,
    WeatherResult,
)
from app.services.advisory_service import AdvisoryService
from app.services.case_store import CaseStore
from app.services.intent_router import IntentRouter
from app.services.metrics_service import MetricsService, build_run_records, estimated_cost
from app.services.policy_engine import PolicyEngine
from app.services.quality_gate import QualityGate
from app.services.vision_service import FakeVisionService, OnnxVisionService, make_vision_service
from app.services.weather_service import WeatherService

T = TypeVar("T")


def _dump(result: object) -> dict | list | None:
    """JSON-safe copy of a service output, for model_runs.output."""
    if isinstance(result, BaseModel):
        return result.model_dump(mode="json")
    if isinstance(result, list) and all(isinstance(r, BaseModel) for r in result):
        return [r.model_dump(mode="json") for r in result]
    return None


class CaseNotFound(LookupError):
    pass


class Orchestrator:
    def __init__(
        self,
        settings: Settings | None = None,
        quality_gate: QualityGate | None = None,
        intent_router: IntentRouter | None = None,
        vision: OnnxVisionService | FakeVisionService | None = None,
        advisory: AdvisoryService | None = None,
        weather: WeatherService | None = None,
    ):
        settings = settings or get_settings()
        self.policy = PolicyEngine(settings)
        self.quality_gate = quality_gate or QualityGate(settings)
        self.intent_router = intent_router or IntentRouter()
        self.vision = vision or make_vision_service(settings)
        self.advisory = advisory or AdvisoryService()
        self.weather = weather or WeatherService()

    def run(self, case: CaseInput) -> OrchestratorResult:
        metrics = MetricsService()
        trace: list[str] = []

        def call(
            route: str,
            model: str,
            fn: Callable[[], T],
            confidence_of: Callable[[T], float | None] = lambda _: None,
        ) -> T | None:
            """Run one model/tool call, time it, log it. Errors are logged and return None."""
            trace.append(route)
            start = time.perf_counter()
            error = None
            try:
                result = fn()
                outcome, conf = "ok", confidence_of(result)
            except Exception as e:  # noqa: BLE001 - any tool failure is handled by policy, not crashed on
                result, outcome, conf, error = None, "error", None, f"{type(e).__name__}: {e}"
            latency = int((time.perf_counter() - start) * 1000)
            metrics.record(
                CallLog(
                    route=route,
                    model=model,
                    latency_ms=latency,
                    cost_usd=estimated_cost(route),
                    confidence=conf,
                    outcome=outcome,
                    error=error,
                    output=_dump(result),
                )
            )
            return result

        def finish(
            d: PolicyDecision,
            label: Category | None = None,
            confidence: float | None = None,
            advisory: AdvisoryResult | None = None,
        ) -> OrchestratorResult:
            trace.append(f"decision:{d.state.value}")
            return OrchestratorResult(
                state=d.state,
                reason=d.reason,
                message=d.message,
                follow_up_question=d.follow_up_question,
                preliminary_label=label,
                confidence=confidence,
                sources=advisory.sources if advisory else [],
                route_trace=trace,
                calls=metrics.calls,
                total_latency_ms=metrics.total_latency_ms(),
                total_cost_usd=metrics.total_cost_usd(),
            )

        # 1. image quality
        q = call(
            "quality_gate",
            self.quality_gate.model_name,
            lambda: self.quality_gate.check(case.close_up_image),
            lambda r: r.score,
        )
        if q is None:
            return finish(self.policy.decide_sources_missing("quality_gate_error"))
        if d := self.policy.check_quality(q):
            return finish(d)

        # 2. crop
        if d := self.policy.check_crop(case.crop):
            return finish(d)

        # 3. intent (keyword rules)
        text = " ".join(filter(None, [case.symptom_context, case.description]))
        intent = call("intent_router", self.intent_router.model_name, lambda: self.intent_router.classify(text))
        if intent is None:
            return finish(self.policy.decide_sources_missing("intent_router_error"))
        if d := self.policy.check_intent(intent):
            return finish(d)

        # 4. vision
        results: list[VisionResult] | None = call(
            "vision",
            self.vision.model_name,
            lambda: self.vision.predict(case.close_up_image),
            lambda rs: max(r.confidence for r in rs),
        )
        if not results:
            return finish(self.policy.decide_sources_missing("vision_error"))

        top = self.policy.pick_top(results)
        tier = self.policy.tier(top.confidence)

        if tier == Tier.LOW:
            return finish(
                self.policy.decide_low(case.field_overview_image is not None), top.label, top.confidence
            )
        if self.policy.models_conflict(results):
            return finish(self.policy.decide_conflict(), top.label, top.confidence)
        if top.label == Category.UNKNOWN:
            return finish(self.policy.decide_unknown_label(), top.label, top.confidence)

        # 5-6. retrieve advisory (and weather at high confidence)
        advisory = call(
            "advisory", self.advisory.model_name, lambda: self.advisory.retrieve(top.label, case.district)
        )
        if advisory is None or not advisory.usable:
            return finish(self.policy.decide_sources_missing("advisory"), top.label, top.confidence)

        weather: WeatherResult | None = None
        if tier == Tier.HIGH:
            weather = call("weather", self.weather.model_name, lambda: self.weather.get(case.district))
            if weather is None or not weather.usable:
                return finish(
                    self.policy.decide_sources_missing("weather"), top.label, top.confidence, advisory
                )

        return finish(
            self.policy.decide_guidance(tier, top.label, advisory, weather),
            top.label,
            top.confidence,
            advisory,
        )


def orchestrate_case(case_id: UUID, store: CaseStore, orchestrator: Orchestrator) -> OrchestratorResult:
    """Load a stored case, run the orchestrator, persist the result plus routing_runs/model_runs."""
    case = store.get_case(case_id)
    if case is None:
        raise CaseNotFound(str(case_id))
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
    routing_runs, model_runs = build_run_records(case_id, result)
    store.save_result(case_id, result)
    store.save_runs(case_id, routing_runs, model_runs)
    return result
