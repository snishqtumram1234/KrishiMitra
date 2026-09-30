"""Response shapes for /api/metrics/*. Every number is computed from routing_runs / model_runs rows."""

from datetime import datetime

from pydantic import BaseModel, Field


class Rate(BaseModel):
    """numerator / denominator, with the counts shown. rate is None when there is nothing to divide by."""

    numerator: int
    denominator: int
    rate: float | None  # 0..1


class LatencyStats(BaseModel):
    n: int
    avg_ms: float | None = None
    p50_ms: float | None = None
    p95_ms: float | None = None  # nearest-rank percentile
    max_ms: float | None = None


class MetricsWindow(BaseModel):
    days: int | None  # None = all time
    since: datetime | None
    generated_at: datetime


class Overview(BaseModel):
    window: MetricsWindow
    total_cases: int  # distinct cases that were analyzed at least once
    total_analyses: int  # routing_runs (a re-analysis or follow-up counts again)
    latency_per_analysis: LatencyStats
    cost_total_usd: float
    cost_per_case_usd: float | None
    cost_per_analysis_usd: float | None
    escalation_rate: Rate  # analyses ending in EXPERT_REVIEW
    abstention_rate: Rate  # analyses that gave no guidance (anything but PRELIMINARY_GUIDANCE)
    vision_abstention_rate: Rate  # of analyses where vision ran: low confidence / unknown label / conflict
    retrieval_success_rate: Rate  # advisory lookups that returned usable (verified, fresh) sources
    cache_hit_rate: Rate  # weather lookups served from the cached snapshot instead of live
    weather_sources: dict[str, int]  # live / cached / demo / unavailable
    model_disagreement_count: int  # analyses where the vision models named different labels
    decision_states: dict[str, int]
    notes: list[str] = Field(default_factory=list)


class PathStats(BaseModel):
    path: str
    count: int
    share: float
    avg_latency_ms: float | None
    avg_cost_usd: float | None
    decision_states: dict[str, int]


class RoutesOut(BaseModel):
    window: MetricsWindow
    total_analyses: int
    by_path: list[PathStats]  # route distribution: which path the orchestrator chose
    by_intent: dict[str, int]
    by_decision_state: dict[str, int]
    vision_call_rate: Rate  # analyses that needed the vision model at all
    skipped_steps: dict[str, int]  # how many times each step was skipped by routing
    estimated_cost_saved_usd: float  # cost of the skipped calls (see ESTIMATED_COST_USD)


class StepStats(BaseModel):
    step: str
    tier: str
    calls: int
    errors: int
    latency: LatencyStats
    total_cost_usd: float
    avg_cost_usd: float | None


class TierStats(BaseModel):
    tier: str  # small_model | vision_model | large_model | tool
    description: str
    calls: int
    share_of_calls: float | None
    total_cost_usd: float
    share_of_cost: float | None


class CostLatencyOut(BaseModel):
    window: MetricsWindow
    total_analyses: int
    latency_per_analysis: LatencyStats
    cost_total_usd: float
    cost_per_analysis_usd: float | None
    cost_per_case_usd: float | None
    by_step: list[StepStats]
    by_tier: list[TierStats]
    estimated_cost_saved_usd: float
    cost_if_vision_always_ran_usd: float | None  # what the same traffic would cost without routing
    notes: list[str] = Field(default_factory=list)
