"""Unit and property tests for Monte Carlo simulation engine."""

import pytest

try:
    from hypothesis import given
    from hypothesis import strategies as st
except ImportError:
    st = None

    def given(*args, **kwargs):
        return pytest.mark.skip(reason="hypothesis not installed")

from app.models.playbook import MonteCarloSimulation
from app.services.monte_carlo import MonteCarloSimulator


def test_monte_carlo_basic_simulation():
    simulator = MonteCarloSimulator(seed=42)
    sim = simulator.simulate(
        ticker="AAPL",
        baseline_price=220.0,
        window_days=3,
        num_simulations=5000,
        implied_move_pct=4.2,
        beat_prob=0.55,
        inline_prob=0.25,
        miss_prob=0.20,
    )

    assert isinstance(sim, MonteCarloSimulation)
    assert sim.ticker == "AAPL"
    assert sim.baseline_price == 220.0
    assert sim.expected_move_pct == 4.2
    assert sim.window_days == 3
    assert sim.num_simulations == 5000
    assert 0.0 <= sim.prob_positive_return <= 100.0
    assert 0.0 <= sim.prob_exceeds_implied_move <= 100.0
    assert sim.expected_range["min"] <= sim.expected_range["max"]

    # Trajectories checks
    assert len(sim.trajectories) == 4  # Day 0, 1, 2, 3
    day0 = sim.trajectories[0]
    assert day0.day == 0
    assert day0.label == "T-0 (Report)"
    assert day0.p5 == day0.p25 == day0.p50 == day0.p75 == day0.p95 == 220.0
    assert day0.p5_return_pct == 0.0

    for traj in sim.trajectories:
        assert traj.p5 <= traj.p25 <= traj.p50 <= traj.p75 <= traj.p95
        assert (
            traj.p5_return_pct
            <= traj.p25_return_pct
            <= traj.p50_return_pct
            <= traj.p75_return_pct
            <= traj.p95_return_pct
        )

    # Risk metrics check
    assert sim.cvar_95_pct <= sim.var_95_pct
    assert len(sim.summary) > 20


def test_monte_carlo_reproducibility():
    sim1 = MonteCarloSimulator(seed=123).simulate(
        ticker="NVDA",
        baseline_price=125.50,
        window_days=3,
        num_simulations=2000,
        implied_move_pct=6.5,
    )
    sim2 = MonteCarloSimulator(seed=123).simulate(
        ticker="NVDA",
        baseline_price=125.50,
        window_days=3,
        num_simulations=2000,
        implied_move_pct=6.5,
    )

    assert sim1.prob_positive_return == sim2.prob_positive_return
    assert sim1.var_95_pct == sim2.var_95_pct
    assert sim1.expected_return_pct == sim2.expected_return_pct
    assert sim1.trajectories[-1].p50 == sim2.trajectories[-1].p50


def test_monte_carlo_outcome_bias():
    # Strong beat bias
    bull_sim = MonteCarloSimulator(seed=999).simulate(
        ticker="MSFT",
        baseline_price=400.0,
        implied_move_pct=5.0,
        beat_prob=0.90,
        inline_prob=0.05,
        miss_prob=0.05,
    )
    # Strong miss bias
    bear_sim = MonteCarloSimulator(seed=999).simulate(
        ticker="MSFT",
        baseline_price=400.0,
        implied_move_pct=5.0,
        beat_prob=0.05,
        inline_prob=0.05,
        miss_prob=0.90,
    )

    assert bull_sim.prob_positive_return > bear_sim.prob_positive_return
    assert bull_sim.expected_return_pct > bear_sim.expected_return_pct
    assert bull_sim.trajectories[-1].p50 > bear_sim.trajectories[-1].p50


def test_monte_carlo_fallback_volatilities():
    simulator = MonteCarloSimulator(seed=42)

    # Only historical move provided
    sim_hist = simulator.simulate(
        ticker="TSLA",
        baseline_price=200.0,
        historical_move_pct=7.8,
    )
    assert sim_hist.expected_move_pct == 7.8

    # No options or historical move provided (uses default 4.5%)
    sim_default = simulator.simulate(
        ticker="XYZ",
        baseline_price=50.0,
    )
    assert sim_default.expected_move_pct == 4.5


def test_monte_carlo_invalid_inputs():
    simulator = MonteCarloSimulator()

    with pytest.raises(ValueError, match="baseline_price must be positive"):
        simulator.simulate(ticker="AAPL", baseline_price=0.0)

    with pytest.raises(ValueError, match="baseline_price must be positive"):
        simulator.simulate(ticker="AAPL", baseline_price=-10.0)

    with pytest.raises(ValueError, match="window_days must be >= 1"):
        simulator.simulate(ticker="AAPL", baseline_price=100.0, window_days=0)

    with pytest.raises(ValueError, match="num_simulations must be >= 100"):
        simulator.simulate(ticker="AAPL", baseline_price=100.0, num_simulations=50)


if st is not None:

    @given(
        price=st.floats(min_value=5.0, max_value=5000.0, allow_nan=False, allow_infinity=False),
        days=st.integers(min_value=1, max_value=5),
        move=st.floats(min_value=0.5, max_value=25.0, allow_nan=False, allow_infinity=False),
    )
    def test_monte_carlo_hypothesis_invariants(price: float, days: int, move: float):
        simulator = MonteCarloSimulator(seed=42)
        sim = simulator.simulate(
            ticker="TEST",
            baseline_price=price,
            window_days=days,
            num_simulations=500,
            implied_move_pct=move,
        )

        assert len(sim.trajectories) == days + 1
        assert 0.0 <= sim.prob_positive_return <= 100.0
        terminal = sim.trajectories[-1]
        assert terminal.p5 <= terminal.p25 <= terminal.p50 <= terminal.p75 <= terminal.p95
        assert sim.cvar_95_pct <= sim.var_95_pct + 1e-4
