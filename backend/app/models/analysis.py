"""Pydantic schemas for analysis engine outputs."""

from datetime import UTC, date, datetime

from pydantic import BaseModel, Field

from app.models.playbook import (
    ConfidenceTier,
    PeerRelationship,
    ReactionArchetype,
    ReactionChartData,
    ReportOutcome,
)


class EarningsReactionEvent(BaseModel):
    """Analyzed reaction for a single historical earnings event."""

    ticker: str
    earnings_date: date
    report_outcome: ReportOutcome | None = None
    initial_move_pct: float
    dip_pct: float | None = None
    recovery_pct: float | None = None
    time_to_bottom_days: int | None = Field(
        default=None,
        description="Trading days from earnings date to window low",
    )
    pattern: ReactionArchetype
    baseline_price: float | None = None
    window_days: int = 3


class MonteCarloSummary(BaseModel):
    """Monte Carlo percentile bands for post-earnings moves."""

    simulations: int
    p10_final_move_pct: float
    p50_final_move_pct: float
    p90_final_move_pct: float
    p10_max_dip_pct: float | None = None
    p50_max_dip_pct: float | None = None
    p90_max_dip_pct: float | None = None
    dip_before_recovery_prob: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description="Fraction of simulations with dip-then-recovery shape",
    )
    mean_final_move_pct: float | None = None


class ValidationSummary(BaseModel):
    """Out-of-sample validation for reaction pattern stability."""

    train_events: int
    test_events: int
    train_dominant_archetype: ReactionArchetype
    test_pattern_match_rate: float = Field(ge=0, le=1)
    pattern_drift: float = Field(ge=0, le=1)
    overfitting_risk: str = Field(description="low, medium, or high")
    is_reliable: bool
    summary: str


class ReactionPatternAnalysis(BaseModel):
    """Aggregate reaction pattern analysis for a ticker."""

    ticker: str
    archetype: ReactionArchetype
    archetype_description: str
    events_analyzed: int
    events: list[EarningsReactionEvent] = Field(default_factory=list)
    pattern_counts: dict[str, int] = Field(default_factory=dict)
    avg_dip_pct: float | None = None
    avg_recovery_pct: float | None = None
    dip_frequency_on_positive: float | None = Field(
        default=None,
        ge=0,
        le=1,
    )
    expected_dip_zone: dict[str, float] | None = Field(
        default=None,
        description="min/max expected dip % on positive outcomes",
    )
    implied_move_pct: float | None = Field(
        default=None,
        description="Options market priced-in implied move % (ATM straddle)",
    )
    historical_move_pct: float | None = Field(
        default=None,
        description="Historical average realized absolute move % on earnings",
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
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    monte_carlo: MonteCarloSummary | None = None
    validation: ValidationSummary | None = None
    backtest_years: float | None = None
    fib_levels: dict[str, float] = Field(default_factory=dict)
    reaction_chart: ReactionChartData | None = None


class PeerCandidate(BaseModel):
    """A candidate peer with correlation metadata."""

    ticker: str
    company_name: str | None = None
    relationship: PeerRelationship
    sector: str | None = None
    correlation_score: float = Field(ge=-1, le=1)
    expected_direction: str = Field(description="same, inverse, weak")
    avg_co_move_pct: float | None = None
    earnings_events_used: int = 0
    rationale: str


class PeerMapResult(BaseModel):
    """Ranked peer spillover map for a reporting ticker."""

    reporting_ticker: str
    sector: str | None = None
    industry: str | None = None
    peers: list[PeerCandidate] = Field(default_factory=list)
    confidence: ConfidenceTier = ConfidenceTier.MEDIUM
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
