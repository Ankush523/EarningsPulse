"""Tests for Monte Carlo reaction simulation."""

from datetime import date

from app.models.analysis import EarningsReactionEvent
from app.models.playbook import ReactionArchetype, ReportOutcome
from app.services.monte_carlo import simulate_reaction_paths


def _event(
    *,
    initial: float,
    dip: float | None,
    recovery: float | None,
) -> EarningsReactionEvent:
    return EarningsReactionEvent(
        ticker="AAPL",
        earnings_date=date(2024, 1, 3),
        report_outcome=ReportOutcome.BEAT,
        initial_move_pct=initial,
        dip_pct=dip,
        recovery_pct=recovery,
        pattern=ReactionArchetype.DIP_THEN_RALLY,
    )


def test_simulate_reaction_paths_returns_percentiles():
    events = [
        _event(initial=2.0, dip=-3.0, recovery=5.0),
        _event(initial=1.0, dip=-1.5, recovery=2.5),
        _event(initial=3.0, dip=-2.0, recovery=4.0),
        _event(initial=-1.0, dip=-4.0, recovery=1.0),
    ]
    result = simulate_reaction_paths(events, n_simulations=500, seed=7)

    assert result is not None
    assert result.simulations == 500
    assert result.p10_final_move_pct <= result.p50_final_move_pct <= result.p90_final_move_pct
    assert result.p50_max_dip_pct is not None
    assert 0 <= (result.dip_before_recovery_prob or 0) <= 1


def test_simulate_reaction_paths_requires_minimum_events():
    events = [
        _event(initial=2.0, dip=-3.0, recovery=5.0),
        _event(initial=1.0, dip=-1.5, recovery=2.5),
    ]
    assert simulate_reaction_paths(events) is None
