"""Pydantic schemas for analysis engine outputs."""

from datetime import UTC, date, datetime

from pydantic import BaseModel, Field

from app.models.playbook import (
    ConfidenceTier,
    MonteCarloSimulation,
    PeerRelationship,
    ReactionArchetype,
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
    monte_carlo: MonteCarloSimulation | None = Field(
        default=None,
        description="Monte Carlo post-earnings price path simulation",
    )
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


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
