"""Monte Carlo simulation engine for post-earnings price paths and return distributions."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from app.models.analysis import MonteCarloPercentilePoint, MonteCarloSimulation


class MonteCarloSimulator:
    """Simulate post-earnings price paths using jump-diffusion Geometric Brownian Motion."""

    def __init__(self, seed: int | None = None):
        self._seed = seed

    def simulate(
        self,
        *,
        ticker: str,
        baseline_price: float,
        window_days: int = 3,
        num_simulations: int = 10000,
        implied_move_pct: float | None = None,
        historical_move_pct: float | None = None,
        expected_move_pct: float | None = None,
        realized_daily_vol_pct: float | None = None,
        beat_prob: float = 0.50,
        inline_prob: float = 0.30,
        miss_prob: float = 0.20,
        seed: int | None = None,
    ) -> MonteCarloSimulation:
        """
        Simulate post-earnings price paths across window_days trading sessions.

        Day 1 models the immediate post-earnings jump shock (calibrated from options
        implied move or historical gap size and weighted by report outcome odds).
        Days 2..T model post-earnings diffusion via Geometric Brownian Motion.
        """
        normalized_ticker = ticker.upper().strip()
        if baseline_price <= 0:
            raise ValueError(f"baseline_price must be positive, got {baseline_price}")

        if window_days < 1:
            raise ValueError(f"window_days must be >= 1, got {window_days}")

        if num_simulations < 100:
            raise ValueError(f"num_simulations must be >= 100, got {num_simulations}")

        effective_seed = seed if seed is not None else self._seed
        rng = np.random.default_rng(effective_seed)

        # 1. Calibrate jump volatility (expected move %)
        jump_vol_pct: float
        if implied_move_pct is not None and implied_move_pct > 0:
            jump_vol_pct = float(implied_move_pct)
        elif historical_move_pct is not None and historical_move_pct > 0:
            jump_vol_pct = float(historical_move_pct)
        elif expected_move_pct is not None and expected_move_pct > 0:
            jump_vol_pct = float(expected_move_pct)
        else:
            jump_vol_pct = 4.5

        sigma_jump = jump_vol_pct / 100.0

        # 2. Calibrate post-earnings daily diffusion volatility
        daily_vol_pct: float
        if realized_daily_vol_pct is not None and realized_daily_vol_pct > 0:
            daily_vol_pct = float(realized_daily_vol_pct)
        else:
            # Typical daily volatility scaled from the jump expectation
            daily_vol_pct = max(1.0, round((jump_vol_pct / math.sqrt(3.0)), 2))

        sigma_daily = daily_vol_pct / 100.0

        # 3. Normalize outcome probabilities
        raw_probs = [max(0.01, beat_prob), max(0.01, inline_prob), max(0.01, miss_prob)]
        total_p = sum(raw_probs)
        norm_probs = [p / total_p for p in raw_probs]

        # Allocate simulation paths array: shape (num_simulations, window_days + 1)
        paths = np.zeros((num_simulations, window_days + 1), dtype=np.float64)
        paths[:, 0] = baseline_price

        # Day 1: Earnings announcement jump
        # Regime 0: Beat (+0.70 * jump_vol mean, 0.45 * jump_vol std)
        # Regime 1: Inline (0.00 mean, 0.35 * jump_vol std)
        # Regime 2: Miss (-0.85 * jump_vol mean, 0.50 * jump_vol std)
        regimes = rng.choice(3, size=num_simulations, p=norm_probs)
        means = np.where(
            regimes == 0,
            0.70 * sigma_jump,
            np.where(regimes == 1, 0.0, -0.85 * sigma_jump),
        )
        stds = np.where(
            regimes == 0,
            0.45 * sigma_jump,
            np.where(regimes == 1, 0.35 * sigma_jump, 0.50 * sigma_jump),
        )

        z1 = rng.standard_normal(num_simulations)
        jump_returns = means + stds * z1
        paths[:, 1] = np.maximum(0.01, baseline_price * (1.0 + jump_returns))

        # Days 2..T: Post-earnings GBM diffusion
        drift = -0.5 * (sigma_daily**2)
        for day in range(2, window_days + 1):
            z = rng.standard_normal(num_simulations)
            step_returns = np.exp(drift + sigma_daily * z)
            paths[:, day] = np.maximum(0.01, paths[:, day - 1] * step_returns)

        # Calculate daily trajectory percentiles
        trajectories: list[MonteCarloPercentilePoint] = []
        for day in range(window_days + 1):
            prices = paths[:, day]
            returns = ((prices - baseline_price) / baseline_price) * 100.0
            label = "T-0 (Report)" if day == 0 else f"T+{day}"

            trajectories.append(
                MonteCarloPercentilePoint(
                    day=day,
                    label=label,
                    p5=round(float(np.percentile(prices, 5)), 2),
                    p25=round(float(np.percentile(prices, 25)), 2),
                    p50=round(float(np.percentile(prices, 50)), 2),
                    p75=round(float(np.percentile(prices, 75)), 2),
                    p95=round(float(np.percentile(prices, 95)), 2),
                    mean=round(float(np.mean(prices)), 2),
                    p5_return_pct=round(float(np.percentile(returns, 5)), 2),
                    p25_return_pct=round(float(np.percentile(returns, 25)), 2),
                    p50_return_pct=round(float(np.percentile(returns, 50)), 2),
                    p75_return_pct=round(float(np.percentile(returns, 75)), 2),
                    p95_return_pct=round(float(np.percentile(returns, 95)), 2),
                )
            )

        # Terminal horizon metrics (at day T)
        terminal_prices = paths[:, -1]
        terminal_returns = ((terminal_prices - baseline_price) / baseline_price) * 100.0

        prob_positive = round(float(np.mean(terminal_returns > 0) * 100.0), 1)
        prob_exceeds_move = round(
            float(np.mean(np.abs(terminal_returns) > jump_vol_pct) * 100.0), 1
        )
        var_95 = round(float(np.percentile(terminal_returns, 5)), 2)
        tail = terminal_returns[terminal_returns <= var_95]
        cvar_95 = round(float(np.mean(tail)), 2) if len(tail) > 0 else var_95

        p5_price = round(float(np.percentile(terminal_prices, 5)), 2)
        p95_price = round(float(np.percentile(terminal_prices, 95)), 2)
        expected_return = round(float(np.mean(terminal_returns)), 2)
        median_return = round(float(np.percentile(terminal_returns, 50)), 2)
        median_price = round(float(np.percentile(terminal_prices, 50)), 2)

        sign = "+" if median_return >= 0 else ""
        summary = (
            f"Across {num_simulations:,} simulated post-earnings paths "
            f"over {window_days} sessions, "
            f"the median price settles at ${median_price:.2f} ({sign}{median_return:.1f}%). "
            f"Win probability is {prob_positive:.1f}%, with a 90% confidence corridor ranging from "
            f"${p5_price:.2f} ({var_95:.1f}%) to ${p95_price:.2f} "
            f"(+{trajectories[-1].p95_return_pct:.1f}%). "
            f"95% Value-at-Risk (VaR) is {var_95:.1f}% (CVaR {cvar_95:.1f}%)."
        )

        return MonteCarloSimulation(
            ticker=normalized_ticker,
            num_simulations=num_simulations,
            window_days=window_days,
            baseline_price=round(baseline_price, 2),
            expected_move_pct=round(jump_vol_pct, 2),
            realized_daily_volatility_pct=round(daily_vol_pct, 2),
            prob_positive_return=prob_positive,
            prob_exceeds_implied_move=prob_exceeds_move,
            var_95_pct=var_95,
            cvar_95_pct=cvar_95,
            expected_range={"min": p5_price, "max": p95_price},
            expected_return_pct=expected_return,
            trajectories=trajectories,
            summary=summary,
        )
