"""Call logging and cost estimation. Builds routing_runs / model_runs rows from an orchestrator run."""

from datetime import UTC, datetime
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
) -> tuple[list[RoutingRunRecord], list[ModelRunRecord]]:
    """One routing_run + one model_run per service call, then one routing_run for the final decision."""
    now = datetime.now(UTC)
    routing: list[RoutingRunRecord] = []
    models: list[ModelRunRecord] = []

    for call in result.calls:
        top = _vision_top(call.output) if call.route == "vision" else None
        intent = call.output.get("intent") if call.route == "intent_router" and isinstance(call.output, dict) else None
        run = RoutingRunRecord(
            id=uuid4(),
            case_id=case_id,
            route=call.route,
            intent=intent,
            confidence=call.confidence,
            latency_ms=call.latency_ms,
            cost_usd=call.cost_usd,
            outcome=call.outcome,
            created_at=now,
        )
        routing.append(run)
        models.append(
            ModelRunRecord(
                id=uuid4(),
                routing_run_id=run.id,
                case_id=case_id,
                model_name=call.model,
                output=call.output,
                predicted_label=top["label"] if top else None,
                confidence=call.confidence,
                latency_ms=call.latency_ms,
                cost_usd=call.cost_usd,
                outcome=call.outcome,
                error=call.error,
                created_at=now,
            )
        )

    routing.append(
        RoutingRunRecord(
            id=uuid4(),
            case_id=case_id,
            route="policy_decision",
            decision_state=result.state,
            confidence=result.confidence,
            reason=result.reason,
            latency_ms=result.total_latency_ms,
            cost_usd=result.total_cost_usd,
            outcome="ok",
            details={"route_trace": result.route_trace},
            created_at=now,
        )
    )
    return routing, models
