"""Monte Carlo simulation for earnings reaction scenarios."""

from __future__ import annotations

import random
from statistics import mean

from app.models.analysis import EarningsReactionEvent, MonteCarloSummary


def simulate_reaction_paths(
    events: list[EarningsReactionEvent],
    *,
    n_simulations: int = 1000,
    seed: int = 42,
) -> MonteCarloSummary | None:
    """
    Bootstrap historical dip/recovery/initial-move distributions.

    Each simulation samples one historical event at random and uses its
    realized metrics as a synthetic post-earnings path.
    """
    if len(events) < 3:
        return None

    rng = random.Random(seed)
    final_moves: list[float] = []
    max_dips: list[float] = []
    dip_then_positive = 0

    for _ in range(n_simulations):
        sample = rng.choice(events)
        initial = sample.initial_move_pct
        dip = sample.dip_pct if sample.dip_pct is not None else initial
        recovery = sample.recovery_pct if sample.recovery_pct is not None else initial

        max_dips.append(dip)
        # Use the stronger of initial close move or recovery high as path outcome proxy.
        final_moves.append(max(initial, recovery))
        if dip <= -0.5 and recovery > abs(dip):
            dip_then_positive += 1

    final_moves.sort()
    max_dips.sort()

    def percentile(values: list[float], pct: float) -> float:
        if not values:
            return 0.0
        idx = int((len(values) - 1) * pct)
        return round(values[idx], 4)

    return MonteCarloSummary(
        simulations=n_simulations,
        p10_final_move_pct=percentile(final_moves, 0.10),
        p50_final_move_pct=percentile(final_moves, 0.50),
        p90_final_move_pct=percentile(final_moves, 0.90),
        p10_max_dip_pct=percentile(max_dips, 0.10),
        p50_max_dip_pct=percentile(max_dips, 0.50),
        p90_max_dip_pct=percentile(max_dips, 0.90),
        dip_before_recovery_prob=round(dip_then_positive / n_simulations, 4),
        mean_final_move_pct=round(mean(final_moves), 4),
    )
