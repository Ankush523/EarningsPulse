"""Convert analysis engine outputs to playbook domain models."""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.analysis import PeerMapResult, ReactionPatternAnalysis
from app.models.playbook import (
    ConfidenceTier,
    HistoricalReaction,
    PeerRelationship,
    PeerSpillover,
    PriceScenario,
    ReactionAnalysisSummary,
    ReactionArchetype,
    ReportOutcome,
    Source,
    SpilloverMap,
)


def reaction_analysis_to_summary(
    analysis: ReactionPatternAnalysis,
) -> ReactionAnalysisSummary:
    """Map ReactionPatternAnalysis to playbook ReactionAnalysisSummary."""
    historical = [
        HistoricalReaction(
            earnings_date=datetime.combine(
                event.earnings_date, datetime.min.time(), tzinfo=timezone.utc
            ),
            report_outcome=event.report_outcome,
            initial_move_pct=event.initial_move_pct,
            dip_pct=event.dip_pct,
            recovery_pct=event.recovery_pct,
            time_to_bottom_minutes=(
                event.time_to_bottom_days * 390
                if event.time_to_bottom_days is not None
                else None
            ),
            pattern=event.pattern,
        )
        for event in analysis.events
    ]

    scenarios = _build_scenarios(analysis)

    return ReactionAnalysisSummary(
        archetype=analysis.archetype,
        archetype_description=analysis.archetype_description,
        scenarios=scenarios,
        historical_reactions=historical,
        avg_dip_pct=analysis.avg_dip_pct,
        avg_recovery_pct=analysis.avg_recovery_pct,
        dip_frequency_on_positive=analysis.dip_frequency_on_positive,
        expected_dip_zone=analysis.expected_dip_zone,
        confidence=analysis.confidence,
        sources=[
            Source(
                title="Historical price data",
                url="https://finance.yahoo.com",
                source_type="price_data",
            )
        ],
    )


def _build_scenarios(analysis: ReactionPatternAnalysis) -> list[PriceScenario]:
    """Build scenario tree from pattern analysis."""
    archetype = analysis.archetype
    dip = analysis.avg_dip_pct
    recovery = analysis.avg_recovery_pct

    if archetype == ReactionArchetype.DIP_THEN_RALLY:
        return [
            PriceScenario(
                outcome=ReportOutcome.BEAT,
                label="Dip-then-rally",
                description="Beat followed by initial dip then recovery (historically common).",
                probability=0.45,
                expected_direction="mixed",
                historical_reference=f"Dominant pattern over {analysis.events_analyzed} events",
                key_levels={
                    "expected_dip_pct": dip or -2.0,
                    "expected_recovery_pct": recovery or 3.0,
                },
            ),
            PriceScenario(
                outcome=ReportOutcome.BEAT,
                label="Immediate rally",
                description="Beat with straight upward move, limited dip.",
                probability=0.30,
                expected_direction="up",
            ),
            PriceScenario(
                outcome=ReportOutcome.BEAT,
                label="Sell the news",
                description="Beat but price fades from highs.",
                probability=0.25,
                expected_direction="down",
            ),
        ]

    if archetype == ReactionArchetype.IMMEDIATE_RIP:
        return [
            PriceScenario(
                outcome=ReportOutcome.BEAT,
                label="Immediate rally",
                description="Positive report leads to straight upward move.",
                probability=0.55,
                expected_direction="up",
            ),
            PriceScenario(
                outcome=ReportOutcome.INLINE,
                label="Volatility chop",
                description="Mixed reaction with two-way volatility.",
                probability=0.25,
                expected_direction="mixed",
            ),
            PriceScenario(
                outcome=ReportOutcome.MISS,
                label="Miss selloff",
                description="Weaker than expected guidance triggers selloff.",
                probability=0.20,
                expected_direction="down",
            ),
        ]

    if archetype == ReactionArchetype.GAP_AND_HOLD:
        return [
            PriceScenario(
                outcome=ReportOutcome.MISS,
                label="Gap and hold",
                description="Miss leads to gap down with limited recovery.",
                probability=0.60,
                expected_direction="down",
            ),
            PriceScenario(
                outcome=ReportOutcome.INLINE,
                label="Dead cat bounce",
                description="Brief bounce after initial drop.",
                probability=0.25,
                expected_direction="mixed",
            ),
            PriceScenario(
                outcome=ReportOutcome.BEAT,
                label="Surprise beat",
                description="Low probability surprise beat scenario.",
                probability=0.15,
                expected_direction="up",
            ),
        ]

    return [
        PriceScenario(
            outcome=ReportOutcome.INLINE,
            label="Range-bound",
            description="Inline report with limited directional follow-through.",
            probability=0.50,
            expected_direction="mixed",
        ),
        PriceScenario(
            outcome=ReportOutcome.BEAT,
            label="Modest beat rally",
            description="Slight upside on a beat.",
            probability=0.30,
            expected_direction="up",
        ),
        PriceScenario(
            outcome=ReportOutcome.MISS,
            label="Modest miss selloff",
            description="Slight downside on a miss.",
            probability=0.20,
            expected_direction="down",
        ),
    ]


def peer_map_to_spillover(result: PeerMapResult) -> SpilloverMap:
    """Map PeerMapResult to playbook SpilloverMap."""
    peers = [
        PeerSpillover(
            ticker=candidate.ticker,
            company_name=candidate.company_name,
            relationship=candidate.relationship,
            correlation_score=candidate.correlation_score,
            expected_direction=candidate.expected_direction,
            rationale=candidate.rationale,
            watch_flag=abs(candidate.correlation_score) >= 0.25,
        )
        for candidate in result.peers
    ]
    return SpilloverMap(
        reporting_ticker=result.reporting_ticker,
        peers=peers,
        confidence=result.confidence,
        sources=[
            Source(
                title="Peer correlation analysis",
                url="https://finance.yahoo.com",
                source_type="price_data",
            )
        ],
    )


def parse_confidence(value: str | ConfidenceTier | None) -> ConfidenceTier:
    if isinstance(value, ConfidenceTier):
        return value
    if not value:
        return ConfidenceTier.MEDIUM
    try:
        return ConfidenceTier(str(value).lower())
    except ValueError:
        return ConfidenceTier.MEDIUM


def parse_peer_relationship(value: str | PeerRelationship) -> PeerRelationship:
    if isinstance(value, PeerRelationship):
        return value
    try:
        return PeerRelationship(str(value).lower())
    except ValueError:
        return PeerRelationship.THEMATIC
