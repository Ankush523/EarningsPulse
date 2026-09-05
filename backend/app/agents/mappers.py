"""Convert analysis engine outputs to playbook domain models."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime

from app.models.analysis import PeerMapResult, ReactionPatternAnalysis
from app.models.playbook import (
    ConfidenceTier,
    HistoricalReaction,
    MonteCarloSummary,
    PeerRelationship,
    PeerSpillover,
    PriceScenario,
    ReactionAnalysisSummary,
    ReactionArchetype,
    ReportOutcome,
    Source,
    SpilloverMap,
    ValidationSummary,
)

POSITIVE_OUTCOMES = {ReportOutcome.BEAT, ReportOutcome.INLINE}

SCENARIO_BY_PATTERN: dict[ReactionArchetype, tuple[str, str, str]] = {
    ReactionArchetype.DIP_THEN_RALLY: (
        "Dip-then-rally",
        "Beat followed by initial dip then recovery (historically common).",
        "mixed",
    ),
    ReactionArchetype.IMMEDIATE_RIP: (
        "Immediate rally",
        "Positive report leads to straight upward move.",
        "up",
    ),
    ReactionArchetype.SELL_THE_NEWS: (
        "Sell the news",
        "Beat but price fades from highs.",
        "down",
    ),
    ReactionArchetype.GAP_AND_HOLD: (
        "Gap and hold",
        "Miss leads to gap down with limited recovery.",
        "down",
    ),
    ReactionArchetype.VOLATILITY_PIN: (
        "Volatility chop",
        "Mixed reaction with two-way volatility.",
        "mixed",
    ),
}


def reaction_analysis_to_summary(
    analysis: ReactionPatternAnalysis,
) -> ReactionAnalysisSummary:
    """Map ReactionPatternAnalysis to playbook ReactionAnalysisSummary."""
    historical = [
        HistoricalReaction(
            earnings_date=datetime.combine(event.earnings_date, datetime.min.time(), tzinfo=UTC),
            report_outcome=event.report_outcome,
            initial_move_pct=event.initial_move_pct,
            dip_pct=event.dip_pct,
            recovery_pct=event.recovery_pct,
            time_to_bottom_minutes=(
                event.time_to_bottom_days * 390 if event.time_to_bottom_days is not None else None
            ),
            pattern=event.pattern,
        )
        for event in analysis.events
    ]

    scenarios = _build_scenarios(analysis)
    monte_carlo = (
        MonteCarloSummary(**analysis.monte_carlo.model_dump())
        if analysis.monte_carlo is not None
        else None
    )
    validation = (
        ValidationSummary(**analysis.validation.model_dump())
        if analysis.validation is not None
        else None
    )

    return ReactionAnalysisSummary(
        archetype=analysis.archetype,
        archetype_description=analysis.archetype_description,
        scenarios=scenarios,
        historical_reactions=historical,
        avg_dip_pct=analysis.avg_dip_pct,
        avg_recovery_pct=analysis.avg_recovery_pct,
        dip_frequency_on_positive=analysis.dip_frequency_on_positive,
        expected_dip_zone=analysis.expected_dip_zone,
        implied_move_pct=analysis.implied_move_pct,
        historical_move_pct=analysis.historical_move_pct,
        volatility_assessment=analysis.volatility_assessment,
        options_summary=analysis.options_summary,
        confidence=analysis.confidence,
        monte_carlo=monte_carlo,
        validation=validation,
        backtest_years=analysis.backtest_years,
        fib_levels=analysis.fib_levels,
        reaction_chart=analysis.reaction_chart,
        sources=[
            Source(
                title="Historical price data",
                url="https://finance.yahoo.com",
                source_type="price_data",
            )
        ],
    )


def _build_scenarios(analysis: ReactionPatternAnalysis) -> list[PriceScenario]:
    """Build scenario tree from backtested pattern frequencies."""
    dip = analysis.avg_dip_pct
    recovery = analysis.avg_recovery_pct
    fib = analysis.fib_levels
    mc = analysis.monte_carlo

    base_levels: dict[str, float] = {}
    if dip is not None:
        base_levels["expected_dip_pct"] = dip
    if recovery is not None:
        base_levels["expected_recovery_pct"] = recovery
    if mc is not None:
        base_levels["mc_p10_final_move_pct"] = mc.p10_final_move_pct
        base_levels["mc_p50_final_move_pct"] = mc.p50_final_move_pct
        base_levels["mc_p90_final_move_pct"] = mc.p90_final_move_pct
        if mc.p50_max_dip_pct is not None:
            base_levels["mc_p50_max_dip_pct"] = mc.p50_max_dip_pct
    for key, value in fib.items():
        if key.endswith("_pct"):
            base_levels[key] = value

    empirical = _empirical_positive_scenarios(analysis)
    if empirical:
        return empirical

    return _fallback_scenarios(analysis, base_levels)


def _empirical_positive_scenarios(
    analysis: ReactionPatternAnalysis,
) -> list[PriceScenario]:
    """Derive beat-path scenario probabilities from historical events."""
    positive_events = [
        event
        for event in analysis.events
        if event.report_outcome in POSITIVE_OUTCOMES or event.initial_move_pct > 0
    ]
    if len(positive_events) < 3:
        return []

    counts = Counter(event.pattern for event in positive_events)
    total = sum(counts.values())
    ordered_patterns = counts.most_common()

    scenarios: list[PriceScenario] = []
    for pattern, count in ordered_patterns[:3]:
        label, description, direction = SCENARIO_BY_PATTERN.get(
            pattern,
            (pattern.value.replace("_", " ").title(), "Historical reaction path.", "mixed"),
        )
        key_levels = _scenario_key_levels(analysis, pattern)
        scenarios.append(
            PriceScenario(
                outcome=ReportOutcome.BEAT,
                label=label,
                description=description,
                probability=round(count / total, 4),
                expected_direction=direction,
                historical_reference=(
                    f"Observed in {count} of {total} positive reactions "
                    f"over {analysis.events_analyzed} backtested events"
                ),
                key_levels=key_levels,
            )
        )

    probability_total = sum(scenario.probability for scenario in scenarios)
    if probability_total <= 0:
        return []
    if abs(probability_total - 1.0) > 0.01:
        scenarios[0].probability = round(
            scenarios[0].probability + (1.0 - probability_total),
            4,
        )
    return scenarios


def _scenario_key_levels(
    analysis: ReactionPatternAnalysis,
    pattern: ReactionArchetype,
) -> dict[str, float]:
    levels: dict[str, float] = {}
    if analysis.avg_dip_pct is not None:
        levels["expected_dip_pct"] = analysis.avg_dip_pct
    if analysis.avg_recovery_pct is not None:
        levels["expected_recovery_pct"] = analysis.avg_recovery_pct
    if analysis.monte_carlo is not None:
        mc = analysis.monte_carlo
        levels["mc_p50_final_move_pct"] = mc.p50_final_move_pct
        if mc.p50_max_dip_pct is not None:
            levels["mc_p50_max_dip_pct"] = mc.p50_max_dip_pct
    for key, value in analysis.fib_levels.items():
        if key.endswith("_pct"):
            levels[key] = value
    if pattern == ReactionArchetype.DIP_THEN_RALLY and not levels.get("expected_dip_pct"):
        levels["expected_dip_pct"] = -2.0
    return levels


def _fallback_scenarios(
    analysis: ReactionPatternAnalysis,
    base_levels: dict[str, float],
) -> list[PriceScenario]:
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
                    **base_levels,
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
                key_levels=base_levels,
            ),
            PriceScenario(
                outcome=ReportOutcome.BEAT,
                label="Sell the news",
                description="Beat but price fades from highs.",
                probability=0.25,
                expected_direction="down",
                key_levels=base_levels,
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
                key_levels=base_levels,
            ),
            PriceScenario(
                outcome=ReportOutcome.INLINE,
                label="Volatility chop",
                description="Mixed reaction with two-way volatility.",
                probability=0.25,
                expected_direction="mixed",
                key_levels=base_levels,
            ),
            PriceScenario(
                outcome=ReportOutcome.MISS,
                label="Miss selloff",
                description="Weaker than expected guidance triggers selloff.",
                probability=0.20,
                expected_direction="down",
                key_levels=base_levels,
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
                key_levels=base_levels,
            ),
            PriceScenario(
                outcome=ReportOutcome.INLINE,
                label="Dead cat bounce",
                description="Brief bounce after initial drop.",
                probability=0.25,
                expected_direction="mixed",
                key_levels=base_levels,
            ),
            PriceScenario(
                outcome=ReportOutcome.BEAT,
                label="Surprise beat",
                description="Low probability surprise beat scenario.",
                probability=0.15,
                expected_direction="up",
                key_levels=base_levels,
            ),
        ]

    return [
        PriceScenario(
            outcome=ReportOutcome.INLINE,
            label="Range-bound",
            description="Inline report with limited directional follow-through.",
            probability=0.50,
            expected_direction="mixed",
            key_levels=base_levels,
        ),
        PriceScenario(
            outcome=ReportOutcome.BEAT,
            label="Modest beat rally",
            description="Slight upside on a beat.",
            probability=0.30,
            expected_direction="up",
            key_levels=base_levels,
        ),
        PriceScenario(
            outcome=ReportOutcome.MISS,
            label="Modest miss selloff",
            description="Slight downside on a miss.",
            probability=0.20,
            expected_direction="down",
            key_levels=base_levels,
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
