"""Call logging and cost estimation. Builds routing_runs / model_runs rows from an orchestrator run."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

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


def estimated_cost(route: str) -> float:
    return ESTIMATED_COST_USD.get(route, 0.0)


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
    intent_call = next((c for c in result.calls if c.route == "intent_router"), None)
    intent = intent_call.output.get("intent") if intent_call and isinstance(intent_call.output, dict) else None

    run = RoutingRunRecord(
        id=uuid4(),
        case_id=case_id,
        route=">".join(steps),
        intent=intent,
        decision_state=result.state,
        confidence=result.confidence,
        reason=result.reason,
        latency_ms=result.total_latency_ms,
        cost_usd=result.total_cost_usd,
        outcome="degraded" if any(c.outcome != "ok" for c in result.calls) else "ok",
        details={"result": result.model_dump(mode="json")},
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
