"""Call logging. In-memory for now; persist to routing_runs / model_runs later."""

from app.schemas.orchestration import CallLog


class MetricsService:
    def __init__(self) -> None:
        self.calls: list[CallLog] = []

    def record(self, log: CallLog) -> None:
        self.calls.append(log)

    def total_latency_ms(self) -> int:
        return sum(c.latency_ms for c in self.calls)

    def total_cost_usd(self) -> float:
        return sum(c.cost_usd for c in self.calls)
