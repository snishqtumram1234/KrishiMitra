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
    Intent,
    CallLog,
    OrchestratorResult,
    PolicyDecision,
    Tier,
    VisionResult,
    WeatherResult,
)
from app.schemas.runs import RoutingRunRecord
from app.services.advisory_service import AdvisoryService
from app.services.case_store import CaseStore
from app.services.intent_router import IntentRouter
from app.services.metrics_service import MetricsService, build_run_records, estimated_cost
from app.services.policy_engine import PolicyEngine
from app.services.quality_gate import QualityGate
from app.services.vision_service import FakeVisionService, OnnxVisionService, make_vision_service
from app.services.weather_service import WeatherService

T = TypeVar("T")

# Every step the orchestrator can call, in order. Anything not called in a run is reported as
# skipped, with the cost it avoided: the visible proof that routing saves work.
PIPELINE = ("intent_router", "quality_gate", "vision", "advisory", "weather")


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
        ctx: dict = {"intent": None, "path": None}

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
            called = {c.route for c in metrics.calls}
            skipped = [s for s in PIPELINE if s not in called]
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
                intent=ctx["intent"].intent if ctx["intent"] else None,
                intent_confidence=ctx["intent"].confidence if ctx["intent"] else None,
                intent_rule=ctx["intent"].rule if ctx["intent"] else None,
                path=ctx["path"],
                skipped_steps=skipped,
                estimated_cost_saved_usd=sum(estimated_cost(s) for s in skipped),
            )

        # 1. crop (the API already enforces soybean; this is defence in depth)
        if d := self.policy.check_crop(case.crop):
            return finish(d)

        # 2. intent (deterministic keyword rules, no model call)
        text = " ".join(filter(None, [case.symptom_context, case.description]))
        has_image = case.close_up_image is not None
        intent = call(
            "intent_router",
            self.intent_router.model_name,
            lambda: self.intent_router.classify(text, has_image=has_image),
            lambda r: r.confidence,
        )
        if intent is None:
            return finish(self.policy.decide_sources_missing("intent_router_error"))
        ctx["intent"] = intent
        if d := self.policy.check_intent(intent):  # expert request, unsupported, unclear
            ctx["path"] = intent.intent.value
            return finish(d)

        # 3. one path per intent
        if intent.intent == Intent.WEATHER_CONTEXT:
            ctx["path"] = "weather"
            weather = call("weather", self.weather.model_name, lambda: self.weather.get(case.district))
            return finish(self.policy.decide_weather(weather))

        if intent.intent == Intent.TREATMENT_SAFETY:
            ctx["path"] = "treatment_safety"
            sources = call(
                "advisory", self.advisory.model_name, lambda: self.advisory.treatment_sources(text, case.district)
            )
            return finish(self.policy.decide_treatment(sources), advisory=sources)

        if intent.intent in (Intent.ADVISORY_LOOKUP, Intent.GENERAL_CROP_QUESTION):
            ctx["path"] = intent.intent.value
            advisory = call("advisory", self.advisory.model_name, lambda: self.advisory.search(text, case.district))
            return finish(self.policy.decide_text_answer(intent.intent, advisory), advisory=advisory)

        ctx["path"] = "image_diagnosis"
        return self._image_path(case, call, finish)

    def _image_path(self, case: CaseInput, call, finish) -> OrchestratorResult:
        """crop_health_image: quality gate -> vision -> confidence tiers -> advisory [+ weather]."""
        q = call(
            "quality_gate",
            self.quality_gate.model_name,
            lambda: self.quality_gate.check(case.close_up_image),
            lambda r: r.score / 100,  # confidence column is 0-1
        )
        if q is None:
            return finish(self.policy.decide_sources_missing("quality_gate_error"))
        if d := self.policy.check_quality(q):
            return finish(d)

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

def orchestrate_case(
    case_id: UUID, store: CaseStore, orchestrator: Orchestrator
) -> tuple[RoutingRunRecord, OrchestratorResult]:
    """Load a stored case, run the orchestrator, persist one routing_run + its model_runs."""
    case = store.get_case(case_id)
    if case is None:
        raise CaseNotFound(str(case_id))
    close_up = store.get_image(case_id, ImageKind.LEAF_CLOSEUP)
    overview = store.get_image(case_id, ImageKind.FIELD_OVERVIEW)

    result = orchestrator.run(
        CaseInput(
            crop=case.crop,
            district=case.district,
            symptom_context=case.symptom_context,
            language=case.language,
            growth_stage=case.growth_stage,
            rainfall=case.recent_rainfall,
            description=case.description,
            close_up_image=close_up.data if close_up else None,
            field_overview_image=overview.data if overview else None,
        )
    )
    run, model_runs = build_run_records(case_id, result)
    store.save_analysis(run, model_runs)
    return run, result
