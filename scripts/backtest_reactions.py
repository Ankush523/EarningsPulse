#!/usr/bin/env python3
"""
Validate earnings reaction patterns on well-known tickers.

Usage:
    cd backend && python ../scripts/backtest_reactions.py
    cd backend && python ../scripts/backtest_reactions.py --tickers AAPL NVDA --limit 40
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.config import get_settings
from app.services.peer_map import PeerMapService
from app.services.reaction_analyzer import ReactionAnalyzer

DEFAULT_TICKERS = ["AAPL", "NVDA", "TSLA", "JPM", "AMZN"]


async def run_backtest(tickers: list[str], limit: int) -> int:
    settings = get_settings()
    analyzer = ReactionAnalyzer(settings=settings)
    peer_service = PeerMapService()

    print("=" * 72)
    print("EarningsPulse — Reaction Pattern Backtest")
    print(f"Lookback: up to {limit} earnings events (~10 years)")
    print("=" * 72)

    for ticker in tickers:
        print(f"\n{'─' * 72}")
        print(f"Ticker: {ticker}")
        print(f"{'─' * 72}")

        try:
            analysis = await analyzer.analyze_ticker(ticker, limit=limit, use_cache=True)
        except Exception as exc:
            print(f"  ✗ Reaction analysis failed: {exc}")
            continue

        print(f"  Archetype:     {analysis.archetype.value}")
        print(f"  Description:   {analysis.archetype_description}")
        print(f"  Events:        {analysis.events_analyzed}")
        if analysis.backtest_years is not None:
            print(f"  Backtest span: {analysis.backtest_years:.1f} years")
        print(f"  Confidence:    {analysis.confidence.value}")
        print(f"  Pattern counts:{analysis.pattern_counts}")

        if analysis.validation:
            print(
                f"  Validation:    {analysis.validation.overfitting_risk} overfitting risk "
                f"({analysis.validation.test_pattern_match_rate * 100:.0f}% holdout match)"
            )
            print(f"                 {analysis.validation.summary}")

        if analysis.monte_carlo:
            mc = analysis.monte_carlo
            print(
                f"  Monte Carlo:   p50 move {mc.p50_final_move_pct:+.2f}% | "
                f"p50 dip {mc.p50_max_dip_pct}% | "
                f"dip-then-recovery {mc.dip_before_recovery_prob * 100:.0f}%"
            )

        if analysis.avg_dip_pct is not None:
            print(f"  Avg dip:       {analysis.avg_dip_pct:.2f}%")
        if analysis.avg_recovery_pct is not None:
            print(f"  Avg recovery:  {analysis.avg_recovery_pct:.2f}%")
        if analysis.dip_frequency_on_positive is not None:
            print(
                f"  Dip freq (+):  {analysis.dip_frequency_on_positive * 100:.1f}%"
            )
        if analysis.expected_dip_zone:
            print(f"  Dip zone:      {analysis.expected_dip_zone}")

        if analysis.events:
            print("  Recent events:")
            for event in analysis.events[:3]:
                print(
                    f"    • {event.earnings_date} | {event.pattern.value} | "
                    f"move {event.initial_move_pct:+.2f}% | "
                    f"dip {event.dip_pct}% | recovery {event.recovery_pct}%"
                )

        try:
            peers = await peer_service.build_peer_map(ticker, max_peers=5, use_cache=True)
            peer_list = ", ".join(
                f"{p.ticker}({p.correlation_score:+.2f})" for p in peers.peers[:5]
            )
            print(f"  Top peers:     {peer_list or 'none'}")
        except Exception as exc:
            print(f"  ✗ Peer map failed: {exc}")

    print(f"\n{'=' * 72}")
    print("Backtest complete.")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backtest earnings reaction patterns")
    parser.add_argument(
        "--tickers",
        nargs="+",
        default=DEFAULT_TICKERS,
        help="Tickers to analyze (default: AAPL NVDA TSLA JPM AMZN)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=get_settings().reaction_history_limit,
        help="Max historical earnings events to analyze (default: from config, 40)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(asyncio.run(run_backtest([t.upper() for t in args.tickers], args.limit)))
