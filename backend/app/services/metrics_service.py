"""Call logging, cost estimation, and the metrics read side.

Write side: MetricsService collects CallLogs during a run; build_run_records turns a finished run
into routing_runs / model_runs rows.
Read side: overview / routes / cost_latency aggregate those stored rows. Nothing is counted in
memory, so the numbers always match what is in the database.
"""

from collections import Counter, defaultdict
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from math import ceil
from uuid import UUID, uuid4

from app.schemas.case import DecisionState
from app.schemas.metrics import (
    CostLatencyOut,
    LatencyStats,
    MetricsWindow,
    Overview,
    PathStats,
    Rate,
    RoutesOut,
    StepStats,
    TierStats,
)
from app.schemas.orchestration import CallLog, OrchestratorResult
from app.schemas.runs import ModelRunRecord, RoutingRunRecord

# Estimated USD per call. Everything runs locally/for free today; the vision figure is a rough
# CPU-inference estimate. Update when paid APIs (weather, LLM, hosted models) are added.
ESTIMATED_COST_USD = {
    "quality_gate": 0.0,
    "intent_router": 0.0,
    "vision": 0.00002,
    "advisory": 0.0,
    "weather": 0.0,
}

# Which kind of model/tool each step is. "large_model" is reserved for LLM calls; none exist yet.
STEP_TIER = {
    "intent_router": "small_model",  # deterministic keyword rules
    "quality_gate": "small_model",  # OpenCV checks
    "vision": "vision_model",  # MobileNetV3 ONNX classifier
    "advisory": "tool",  # retrieval
    "weather": "tool",  # Open-Meteo adapter
}
TIER_DESCRIPTION = {
    "small_model": "Rules and classical CV (intent router, OpenCV quality gate)",
    "vision_model": "Soybean vision classifier (ONNX)",
    "large_model": "LLM calls (none used yet)",
    "tool": "Retrieval and data tools (advisory, weather)",
}
TIER_ORDER = ["small_model", "vision_model", "large_model", "tool"]
ABSTENTION_REASON_PREFIXES = ("low_confidence", "label_unknown", "models_conflict")


def estimated_cost(route: str) -> float:
    return ESTIMATED_COST_USD.get(route, 0.0)


def tier_of(step: str) -> str:
    return STEP_TIER.get(step, "tool")


# ================================================================ write side
class MetricsService:
    def __init__(self) -> None:
        self.calls: list[CallLog] = []

    def record(self, log: CallLog) -> None:
        self.calls.append(log)

    def total_latency_ms(self) -> int:
        return sum(c.latency_ms for c in self.calls)

    def total_cost_usd(self) -> float:
        return sum(c.cost_usd for c in self.calls)


def _vision_top(output: dict | list | None) -> dict | None:
    if isinstance(output, list) and output:
        return max(output, key=lambda r: r.get("confidence", 0.0))
    return None


def build_run_records(
    case_id: UUID, result: OrchestratorResult
) -> tuple[RoutingRunRecord, list[ModelRunRecord]]:
    """One routing_run for the whole analysis + one model_run per service call."""
    now = datetime.now(UTC)
    steps = [c.route for c in result.calls]

    run = RoutingRunRecord(
        id=uuid4(),
        case_id=case_id,
        route=result.path or "none",
        intent=result.intent.value if result.intent else None,
        decision_state=result.state,
        confidence=result.confidence,
        reason=result.reason,
        latency_ms=result.total_latency_ms,
        cost_usd=result.total_cost_usd,
        outcome="degraded" if any(c.outcome != "ok" for c in result.calls) else "ok",
        details={
            "steps": steps,
            "intent_rule": result.intent_rule,
            "intent_confidence": result.intent_confidence,
            "result": result.model_dump(mode="json"),
        },
        created_at=now,
    )
    models = []
    for i, call in enumerate(result.calls):
        top = _vision_top(call.output) if call.route == "vision" else None
        models.append(
            ModelRunRecord(
                id=uuid4(),
                routing_run_id=run.id,
                case_id=case_id,
                step=call.route,
                model_name=call.model,
                output=call.output,
                predicted_label=top["label"] if top else None,
                confidence=call.confidence,
                latency_ms=call.latency_ms,
                cost_usd=call.cost_usd,
                outcome=call.outcome,
                error=call.error,
                created_at=now + timedelta(microseconds=i),  # keeps step order on created_at sort
            )
        )
    return run, models


# ================================================================ read side (aggregation)
def rate(numerator: int, denominator: int) -> Rate:
    return Rate(numerator=numerator, denominator=denominator,
                rate=round(numerator / denominator, 4) if denominator else None)


def percentile(sorted_values: list[float], p: float) -> float:
    """Nearest-rank percentile of an already sorted, non-empty list."""
    return sorted_values[max(0, ceil(p / 100 * len(sorted_values)) - 1)]


def latency_stats(values: Iterable[float]) -> LatencyStats:
    vals = sorted(values)
    if not vals:
        return LatencyStats(n=0)
    return LatencyStats(n=len(vals), avg_ms=round(sum(vals) / len(vals), 2), p50_ms=percentile(vals, 50),
                        p95_ms=percentile(vals, 95), max_ms=vals[-1])


def make_window(days: int | None, now: datetime | None = None) -> MetricsWindow:
    now = now or datetime.now(UTC)
    return MetricsWindow(days=days, since=now - timedelta(days=days) if days else None, generated_at=now)


def _per_case_cost(runs: list[RoutingRunRecord]) -> float | None:
    cases = {r.case_id for r in runs}
    return round(sum(r.cost_usd for r in runs) / len(cases), 8) if cases else None


def _vision_labels(m: ModelRunRecord) -> set[str]:
    return {p.get("label") for p in m.output if isinstance(p, dict)} if isinstance(m.output, list) else set()


def _advisory_usable(m: ModelRunRecord) -> bool:
    """Same rule as AdvisoryResult.usable: at least one source, all verified and not stale."""
    if m.outcome != "ok" or not isinstance(m.output, dict):
        return False
    sources = m.output.get("sources") or []
    return bool(sources) and all(s.get("verified") and not s.get("stale") for s in sources)


def _result(r: RoutingRunRecord) -> dict:
    return (r.details or {}).get("result") or {}


def overview(runs: list[RoutingRunRecord], models: list[ModelRunRecord], window: MetricsWindow) -> Overview:
    n = len(runs)
    states = Counter(r.decision_state.value for r in runs if r.decision_state)
    escalated = states[DecisionState.EXPERT_REVIEW.value]
    abstained = n - states[DecisionState.PRELIMINARY_GUIDANCE.value]

    vision_runs = {m.routing_run_id for m in models if m.step == "vision" and m.outcome == "ok"}
    vision_abstained = sum(
        1 for r in runs if r.id in vision_runs and (r.reason or "").startswith(ABSTENTION_REASON_PREFIXES)
    )

    advisory = [m for m in models if m.step == "advisory"]
    weather = [m for m in models if m.step == "weather"]
    weather_sources = Counter(
        (m.output or {}).get("source", "unavailable") if m.outcome == "ok" and isinstance(m.output, dict)
        else "error"
        for m in weather
    )
    disagreements = sum(1 for m in models if m.step == "vision" and len(_vision_labels(m)) > 1)

    notes = []
    if not any(m.step == "vision" and isinstance(m.output, list) and len(m.output) > 1 for m in models):
        notes.append("Only one vision model is deployed, so model disagreement cannot occur yet (count is 0 by construction).")
    if weather and not weather_sources.get("cached"):
        notes.append("No weather lookup was served from cache in this window (the cache is used only when the live source fails).")

    return Overview(
        window=window,
        total_cases=len({r.case_id for r in runs}),
        total_analyses=n,
        latency_per_analysis=latency_stats(r.latency_ms for r in runs),
        cost_total_usd=round(sum(r.cost_usd for r in runs), 8),
        cost_per_case_usd=_per_case_cost(runs),
        cost_per_analysis_usd=round(sum(r.cost_usd for r in runs) / n, 8) if n else None,
        escalation_rate=rate(escalated, n),
        abstention_rate=rate(abstained, n),
        vision_abstention_rate=rate(vision_abstained, len(vision_runs)),
        retrieval_success_rate=rate(sum(_advisory_usable(m) for m in advisory), len(advisory)),
        cache_hit_rate=rate(weather_sources.get("cached", 0), len(weather)),
        weather_sources=dict(weather_sources),
        model_disagreement_count=disagreements,
        decision_states=dict(states),
        notes=notes,
    )


def routes(runs: list[RoutingRunRecord], models: list[ModelRunRecord], window: MetricsWindow) -> RoutesOut:
    n = len(runs)
    by_path: dict[str, list[RoutingRunRecord]] = defaultdict(list)
    for r in runs:
        by_path[r.route].append(r)
    path_stats = [
        PathStats(
            path=path,
            count=len(rs),
            share=round(len(rs) / n, 4),
            avg_latency_ms=round(sum(r.latency_ms for r in rs) / len(rs), 2),
            avg_cost_usd=round(sum(r.cost_usd for r in rs) / len(rs), 8),
            decision_states=dict(Counter(r.decision_state.value for r in rs if r.decision_state)),
        )
        for path, rs in sorted(by_path.items(), key=lambda kv: -len(kv[1]))
    ]
    skipped = Counter(s for r in runs for s in _result(r).get("skipped_steps", []))
    saved = sum(_result(r).get("estimated_cost_saved_usd", 0.0) for r in runs)
    vision_runs = {m.routing_run_id for m in models if m.step == "vision"}
    return RoutesOut(
        window=window,
        total_analyses=n,
        by_path=path_stats,
        by_intent=dict(Counter(r.intent for r in runs if r.intent)),
        by_decision_state=dict(Counter(r.decision_state.value for r in runs if r.decision_state)),
        vision_call_rate=rate(sum(1 for r in runs if r.id in vision_runs), n),
        skipped_steps=dict(skipped),
        estimated_cost_saved_usd=round(saved, 8),
    )


def cost_latency(runs: list[RoutingRunRecord], models: list[ModelRunRecord], window: MetricsWindow) -> CostLatencyOut:
    n = len(runs)
    by_step: dict[str, list[ModelRunRecord]] = defaultdict(list)
    for m in models:
        by_step[m.step].append(m)
    steps = [
        StepStats(
            step=step,
            tier=tier_of(step),
            calls=len(ms),
            errors=sum(1 for m in ms if m.outcome != "ok"),
            latency=latency_stats(m.latency_ms for m in ms),
            total_cost_usd=round(sum(m.cost_usd for m in ms), 8),
            avg_cost_usd=round(sum(m.cost_usd for m in ms) / len(ms), 8),
        )
        for step, ms in sorted(by_step.items(), key=lambda kv: -len(kv[1]))
    ]
    total_calls = len(models)
    total_cost = sum(m.cost_usd for m in models)
    tiers = []
    for tier in TIER_ORDER:
        ms = [m for m in models if tier_of(m.step) == tier]
        cost = sum(m.cost_usd for m in ms)
        tiers.append(TierStats(
            tier=tier, description=TIER_DESCRIPTION[tier], calls=len(ms),
            share_of_calls=round(len(ms) / total_calls, 4) if total_calls else None,
            total_cost_usd=round(cost, 8),
            share_of_cost=round(cost / total_cost, 4) if total_cost else None,
        ))
    saved = sum(_result(r).get("estimated_cost_saved_usd", 0.0) for r in runs)
    actual = sum(r.cost_usd for r in runs)
    vision_skipped = sum(1 for r in runs if "vision" in _result(r).get("skipped_steps", []))
    return CostLatencyOut(
        window=window,
        total_analyses=n,
        latency_per_analysis=latency_stats(r.latency_ms for r in runs),
        cost_total_usd=round(actual, 8),
        cost_per_analysis_usd=round(actual / n, 8) if n else None,
        cost_per_case_usd=_per_case_cost(runs),
        by_step=steps,
        by_tier=tiers,
        estimated_cost_saved_usd=round(saved, 8),
        cost_if_vision_always_ran_usd=round(actual + vision_skipped * estimated_cost("vision"), 8) if n else None,
        notes=[
            "Costs are estimates from ESTIMATED_COST_USD (local CPU inference and free APIs), not billed amounts.",
            "cost_if_vision_always_ran_usd is a what-if: the same traffic if every analysis also called the vision model.",
        ],
    )
