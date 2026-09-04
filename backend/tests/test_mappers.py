"""Unit tests for analysis → playbook mappers."""

from datetime import date

from app.agents.mappers import reaction_analysis_to_summary
from app.models.analysis import EarningsReactionEvent, ReactionPatternAnalysis
from app.models.playbook import ReactionArchetype


def _analysis_with_days(days: int | None) -> ReactionPatternAnalysis:
    return ReactionPatternAnalysis(
        ticker="AAPL",
        archetype=ReactionArchetype.DIP_THEN_RALLY,
        archetype_description="test",
        events_analyzed=1,
        events=[
            EarningsReactionEvent(
                ticker="AAPL",
                earnings_date=date(2024, 1, 2),
                initial_move_pct=-1.5,
                dip_pct=-2.0,
                recovery_pct=1.0,
                time_to_bottom_days=days,
                pattern=ReactionArchetype.DIP_THEN_RALLY,
            )
        ],
    )


def test_zero_trading_days_maps_to_zero_minutes():
    mapped = reaction_analysis_to_summary(_analysis_with_days(0))
    assert mapped.historical_reactions[0].time_to_bottom_minutes == 0


def test_missing_trading_days_maps_to_none_minutes():
    mapped = reaction_analysis_to_summary(_analysis_with_days(None))
    assert mapped.historical_reactions[0].time_to_bottom_minutes is None


def test_nonzero_trading_days_maps_to_minutes():
    mapped = reaction_analysis_to_summary(_analysis_with_days(2))
    assert mapped.historical_reactions[0].time_to_bottom_minutes == 2 * 390
