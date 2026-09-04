"""Tests for out-of-sample reaction validation."""

from datetime import date

from app.models.analysis import EarningsReactionEvent
from app.models.playbook import ReactionArchetype, ReportOutcome
from app.services.reaction_validation import validate_reaction_patterns


def _event(day: int, pattern: ReactionArchetype) -> EarningsReactionEvent:
    return EarningsReactionEvent(
        ticker="NVDA",
        earnings_date=date(2020, 1, day),
        report_outcome=ReportOutcome.BEAT,
        initial_move_pct=2.0,
        dip_pct=-2.0,
        recovery_pct=4.0,
        pattern=pattern,
    )


def test_validate_reaction_patterns_stable_pattern():
    events = [_event(i, ReactionArchetype.DIP_THEN_RALLY) for i in range(1, 11)]
    result = validate_reaction_patterns(events, train_ratio=0.7)

    assert result is not None
    assert result.train_events == 7
    assert result.test_events == 3
    assert result.test_pattern_match_rate == 1.0
    assert result.overfitting_risk == "low"
    assert result.is_reliable is True


def test_validate_reaction_patterns_detects_drift():
    train = [_event(i, ReactionArchetype.DIP_THEN_RALLY) for i in range(1, 8)]
    test = [_event(i, ReactionArchetype.GAP_AND_HOLD) for i in range(8, 11)]
    result = validate_reaction_patterns(train + test, train_ratio=0.7)

    assert result is not None
    assert result.test_pattern_match_rate == 0.0
    assert result.overfitting_risk == "high"
    assert result.is_reliable is False


def test_validate_reaction_patterns_requires_enough_events():
    events = [_event(i, ReactionArchetype.DIP_THEN_RALLY) for i in range(1, 5)]
    assert validate_reaction_patterns(events) is None
