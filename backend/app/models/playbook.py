"""Pydantic schemas for the Earnings Playbook deliverable."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


class ConfidenceTier(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ReportOutcome(str, Enum):
    BEAT = "beat"
    INLINE = "inline"
    MISS = "miss"


class ReactionArchetype(str, Enum):
    DIP_THEN_RALLY = "dip_then_rally"
    IMMEDIATE_RIP = "immediate_rip"
    SELL_THE_NEWS = "sell_the_news"
    GAP_AND_HOLD = "gap_and_hold"
    VOLATILITY_PIN = "volatility_pin"
    INSUFFICIENT_DATA = "insufficient_data"


class PeerRelationship(str, Enum):
    DIRECT_PEER = "direct_peer"
    SUPPLIER = "supplier"
    CUSTOMER = "customer"
    THEMATIC = "thematic"


class Source(BaseModel):
    """A citable source for a factual claim."""

    title: str
    url: str
    source_type: str = Field(description="Type: filing, news, price_data, estimate, tavily, edgar")
    accessed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ExecutiveSummary(BaseModel):
    """Section A — Executive summary."""

    ticker: str
    company_name: str | None = None
    earnings_date: datetime | None = None
    is_after_hours: bool = True
    beat_probability: float = Field(ge=0, le=1)
    inline_probability: float = Field(ge=0, le=1)
    miss_probability: float = Field(ge=0, le=1)
    primary_pattern: ReactionArchetype
    primary_pattern_description: str
    overall_confidence: ConfidenceTier
    top_drivers: list[str] = Field(min_length=1, max_length=5)
    sources: list[Source] = Field(default_factory=list)


class KeyMetric(BaseModel):
    """A metric to watch in the upcoming report."""

    name: str
    description: str
    importance: ConfidenceTier = ConfidenceTier.MEDIUM


class ReportForecast(BaseModel):
    """Section B — Report forecast."""

    key_metrics: list[KeyMetric] = Field(default_factory=list)
    bull_case: str
    base_case: str
    bear_case: str
    positive_surprises: list[str] = Field(default_factory=list)
    negative_surprises: list[str] = Field(default_factory=list)
    confidence: ConfidenceTier = ConfidenceTier.MEDIUM
    sources: list[Source] = Field(default_factory=list)


class PriceScenario(BaseModel):
    """A single price reaction scenario."""

    outcome: ReportOutcome
    label: str
    description: str
    probability: float = Field(ge=0, le=1)
    expected_direction: str = Field(description="up, down, mixed")
    historical_reference: str | None = None
    key_levels: dict[str, float] = Field(default_factory=dict)


class HistoricalReaction(BaseModel):
    """Single past earnings reaction data point."""

    earnings_date: datetime
    report_outcome: ReportOutcome | None = None
    initial_move_pct: float
    dip_pct: float | None = None
    recovery_pct: float | None = None
    time_to_bottom_minutes: int | None = None
    pattern: ReactionArchetype


class MonteCarloPercentilePoint(BaseModel):
    """Percentile price and return at a specific day in the simulation window."""

    day: int = Field(description="Trading day relative to earnings (0 = pre-earnings baseline)")
    label: str = Field(description="Day label (e.g. T-0, T+1, T+2, T+3)")
    p5: float = Field(description="5th percentile price")
    p25: float = Field(description="25th percentile price")
    p50: float = Field(description="50th percentile / median price")
    p75: float = Field(description="75th percentile price")
    p95: float = Field(description="95th percentile price")
    mean: float = Field(description="Mean simulated price")
    p5_return_pct: float
    p25_return_pct: float
    p50_return_pct: float
    p75_return_pct: float
    p95_return_pct: float


class MonteCarloSimulation(BaseModel):
    """Monte Carlo price path simulation output."""

    ticker: str
    num_simulations: int = Field(default=10000, description="Number of simulated trajectories")
    window_days: int = Field(default=3, description="Simulation horizon in trading days")
    baseline_price: float = Field(description="Pre-earnings baseline price")
    expected_move_pct: float = Field(description="Expected earnings jump volatility %")
    realized_daily_volatility_pct: float = Field(
        description="Daily volatility % used for diffusion"
    )
    prob_positive_return: float = Field(
        ge=0, le=100, description="Probability of positive return at horizon %"
    )
    prob_exceeds_implied_move: float = Field(
        ge=0, le=100, description="Probability of exceeding implied move %"
    )
    var_95_pct: float = Field(description="95% Value at Risk %")
    cvar_95_pct: float = Field(description="95% Expected Shortfall / CVaR %")
    expected_range: dict[str, float] = Field(description="min/max expected price at window end")
    expected_return_pct: float = Field(description="Mean expected return % across all simulations")
    trajectories: list[MonteCarloPercentilePoint] = Field(default_factory=list)
    summary: str = Field(description="Human-readable synthesis of simulation findings")


class ReactionAnalysisSummary(BaseModel):
    """Section C — Price reaction scenarios and historical analysis."""

    archetype: ReactionArchetype
    archetype_description: str
    scenarios: list[PriceScenario] = Field(default_factory=list)
    historical_reactions: list[HistoricalReaction] = Field(default_factory=list)
    avg_dip_pct: float | None = None
    avg_recovery_pct: float | None = None
    dip_frequency_on_positive: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description="Fraction of positive reports that dipped first",
    )
    expected_dip_zone: dict[str, float] | None = Field(
        default=None,
        description="min/max expected dip % if beat",
    )
    implied_move_pct: float | None = Field(
        default=None,
        description="Options market priced-in implied move % (ATM straddle)",
    )
    historical_move_pct: float | None = Field(
        default=None,
        description="Historical average realized move % on past earnings",
    )
    volatility_assessment: str | None = Field(
        default=None,
        description="Comparison: OVERPRICED, UNDERPRICED, or INLINE",
    )
    options_summary: str | None = Field(
        default=None,
        description="Summary of options implied move vs historical realized move",
    )
    confidence: ConfidenceTier = ConfidenceTier.MEDIUM
    monte_carlo: MonteCarloSimulation | None = Field(
        default=None,
        description="Monte Carlo post-earnings price path simulation",
    )
    sources: list[Source] = Field(default_factory=list)


class PeerSpillover(BaseModel):
    """A single peer in the spillover map."""

    ticker: str
    company_name: str | None = None
    relationship: PeerRelationship
    correlation_score: float = Field(ge=-1, le=1)
    expected_direction: str = Field(description="same, inverse, weak")
    rationale: str
    watch_flag: bool = True


class SpilloverMap(BaseModel):
    """Section D — Peer spillover map."""

    reporting_ticker: str
    peers: list[PeerSpillover] = Field(default_factory=list)
    confidence: ConfidenceTier = ConfidenceTier.MEDIUM
    sources: list[Source] = Field(default_factory=list)


class ActionRule(BaseModel):
    """A single if/then action rule."""

    condition: str
    action: str
    confidence: ConfidenceTier = ConfidenceTier.MEDIUM
    historical_basis: str | None = None


class ActionPlaybook(BaseModel):
    """Section E — Action playbook (decision support)."""

    rules: list[ActionRule] = Field(default_factory=list)
    disclaimer: str = "Not financial advice. For informational and decision-support purposes only."


class PlaybookMetadata(BaseModel):
    """Metadata about playbook generation."""

    job_id: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    generation_time_ms: int | None = None
    model_version: str = "0.1.0"
    data_sources_used: list[str] = Field(default_factory=list)


class Playbook(BaseModel):
    """Complete Earnings Playbook — the primary user-facing deliverable."""

    metadata: PlaybookMetadata
    executive_summary: ExecutiveSummary
    report_forecast: ReportForecast
    reaction_analysis: ReactionAnalysisSummary
    spillover_map: SpilloverMap
    action_playbook: ActionPlaybook
    all_sources: list[Source] = Field(default_factory=list)
    trace_id: str | None = None


class PlaybookGenerateRequest(BaseModel):
    """Request to generate a playbook."""

    ticker: str = Field(min_length=1, max_length=10, pattern=r"^[A-Za-z.\-]+$")
    earnings_date: datetime | None = None


class PlaybookGenerateResponse(BaseModel):
    """Response when playbook generation is started."""

    job_id: str
    ticker: str
    status: str = "pending"
    stream_url: str


class PlaybookStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class JobStatus(BaseModel):
    """Status of a playbook generation job."""

    job_id: str
    ticker: str
    status: PlaybookStatus
    playbook: Playbook | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
