"""Tests for reaction chart payload builder."""

from datetime import date

from app.models.analysis import EarningsReactionEvent, ReactionPatternAnalysis
from app.models.data import OHLCVBar
from app.models.playbook import ConfidenceTier, ReactionArchetype, ReportOutcome
from app.services.reaction_chart import build_reaction_chart_data


def _bars(center: date, *, base: float = 100.0, span: int = 3) -> list[OHLCVBar]:
    offsets = range(-span, span + 1)
    bars: list[OHLCVBar] = []
    for index, offset in enumerate(offsets):
        day = center.fromordinal(center.toordinal() + offset)
        close = base + index * 0.8
        bars.append(
            OHLCVBar(
                date=day,
                open=close - 0.4,
                high=close + 0.6,
                low=close - 0.8,
                close=close,
                volume=1_000_000 + index * 10_000,
            )
        )
    return bars


def _analysis() -> ReactionPatternAnalysis:
    return ReactionPatternAnalysis(
        ticker="AAPL",
        archetype=ReactionArchetype.DIP_THEN_RALLY,
        archetype_description="Dip-then-rally",
        events_analyzed=1,
        confidence=ConfidenceTier.MEDIUM,
        implied_move_pct=4.0,
        avg_dip_pct=-2.5,
        avg_recovery_pct=3.0,
    )


def test_build_reaction_chart_data_includes_candles_and_trading_lines():
    earnings_date = date(2024, 5, 2)
    bars = _bars(earnings_date, span=50)
    events = [
        EarningsReactionEvent(
            ticker="AAPL",
            earnings_date=earnings_date,
            report_outcome=ReportOutcome.BEAT,
            initial_move_pct=1.2,
            dip_pct=-1.5,
            recovery_pct=2.0,
            pattern=ReactionArchetype.DIP_THEN_RALLY,
            baseline_price=100.0,
        )
    ]

    chart = build_reaction_chart_data(
        "AAPL",
        events,
        bars,
        _analysis(),
        window_days=3,
    )

    assert chart is not None
    assert chart.ticker == "AAPL"
    assert len(chart.candles) >= 10
    assert len(chart.paths) == 1
    assert len(chart.median_path) >= 2
    kinds = {line.kind for line in chart.reference_lines}
    assert "entry" in kinds
    assert "pivot" in kinds
    assert "support" in kinds
    assert "resistance" in kinds
    assert "tp" in kinds
    assert "sl" in kinds


def test_build_reaction_chart_data_returns_none_without_bars():
    earnings_date = date(2024, 5, 2)
    events = [
        EarningsReactionEvent(
            ticker="AAPL",
            earnings_date=earnings_date,
            report_outcome=ReportOutcome.BEAT,
            initial_move_pct=1.2,
            pattern=ReactionArchetype.DIP_THEN_RALLY,
            baseline_price=100.0,
        )
    ]

    assert build_reaction_chart_data("AAPL", events, [], _analysis(), window_days=3) is None
