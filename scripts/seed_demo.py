#!/usr/bin/env python3
"""
Pre-cache demo playbooks for instant hackathon demos.

Usage:
  cd backend

  # Mock demo (no API keys required)
  uv run python ../scripts/seed_demo.py --offline --ticker AAPL

  # Live demo (requires Phase 1–3 env keys)
  uv run python ../scripts/seed_demo.py --ticker AAPL
  uv run python ../scripts/seed_demo.py --ticker NVDA --ticker MSFT
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow running from repo root or backend/
BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.agents.orchestrator import PlaybookOrchestrator
from app.agents.trace_utils import make_trace_event, trace_to_dict
from app.config import get_settings
from app.models.playbook import (
    ActionPlaybook,
    ActionRule,
    ConfidenceTier,
    ExecutiveSummary,
    KeyMetric,
    PeerSpillover,
    Playbook,
    PlaybookMetadata,
    PriceScenario,
    ReactionAnalysisSummary,
    ReactionArchetype,
    ReportForecast,
    ReportOutcome,
    SpilloverMap,
)
from app.models.trace import TraceEventType, TraceLog
from app.services.demo_store import DemoCacheEntry, DemoStore


def build_offline_playbook(ticker: str, job_id: str) -> Playbook:
    """Build a realistic mock playbook for offline demo mode."""
    return Playbook(
        metadata=PlaybookMetadata(
            job_id=job_id,
            generation_time_ms=1250,
            data_sources_used=["tavily", "yfinance", "edgar", "finnhub"],
        ),
        executive_summary=ExecutiveSummary(
            ticker=ticker,
            company_name="Apple Inc." if ticker == "AAPL" else f"{ticker} Inc.",
            earnings_date=datetime.now(timezone.utc),
            is_after_hours=True,
            beat_probability=0.52,
            inline_probability=0.28,
            miss_probability=0.20,
            primary_pattern=ReactionArchetype.DIP_THEN_RALLY,
            primary_pattern_description=(
                "Historical pattern shows initial volatility after beats, "
                "often dipping before a multi-day recovery."
            ),
            overall_confidence=ConfidenceTier.MEDIUM,
            top_drivers=[
                "Services revenue growth trajectory",
                "iPhone demand in China",
                "Margin guidance for next quarter",
                "Buyback and capital return cadence",
            ],
        ),
        report_forecast=ReportForecast(
            key_metrics=[
                KeyMetric(
                    name="Services revenue",
                    description="High-margin recurring revenue stream",
                    importance=ConfidenceTier.HIGH,
                ),
                KeyMetric(
                    name="Gross margin",
                    description="Product mix and cost discipline",
                    importance=ConfidenceTier.MEDIUM,
                ),
            ],
            bull_case="Beat on Services with raised full-year guidance.",
            base_case="Inline report with stable margins.",
            bear_case="Soft iPhone units and cautious outlook.",
            positive_surprises=["Services beat", "Strong installed base"],
            negative_surprises=["China headwinds", "FX drag"],
            confidence=ConfidenceTier.MEDIUM,
        ),
        reaction_analysis=ReactionAnalysisSummary(
            archetype=ReactionArchetype.DIP_THEN_RALLY,
            archetype_description="Dip-then-rally after positive reports",
            scenarios=[
                PriceScenario(
                    outcome=ReportOutcome.BEAT,
                    label="Beat → dip → rally",
                    description="Initial sell-the-news dip, then recovery over 2–3 sessions.",
                    probability=0.45,
                    expected_direction="mixed",
                    historical_reference="Observed on 3 of last 4 beats",
                ),
                PriceScenario(
                    outcome=ReportOutcome.INLINE,
                    label="Inline → muted",
                    description="Limited move, range-bound reaction.",
                    probability=0.30,
                    expected_direction="mixed",
                ),
                PriceScenario(
                    outcome=ReportOutcome.MISS,
                    label="Miss → gap down",
                    description="Sharp downside with limited same-day recovery.",
                    probability=0.25,
                    expected_direction="down",
                ),
            ],
            historical_reactions=[],
            avg_dip_pct=-2.8,
            avg_recovery_pct=4.1,
            dip_frequency_on_positive=0.75,
            expected_dip_zone={"min": -4.0, "max": -1.5, "median": -2.8},
            confidence=ConfidenceTier.MEDIUM,
        ),
        spillover_map=SpilloverMap(
            reporting_ticker=ticker,
            peers=[
                PeerSpillover(
                    ticker="MSFT",
                    company_name="Microsoft",
                    relationship="direct_peer",
                    correlation_score=0.58,
                    expected_direction="same",
                    rationale="Large-cap tech sentiment linkage",
                    watch_flag=True,
                ),
                PeerSpillover(
                    ticker="GOOGL",
                    company_name="Alphabet",
                    relationship="direct_peer",
                    correlation_score=0.51,
                    expected_direction="same",
                    rationale="Mag7 peer earnings read-through",
                    watch_flag=True,
                ),
            ],
            confidence=ConfidenceTier.MEDIUM,
        ),
        action_playbook=ActionPlaybook(
            rules=[
                ActionRule(
                    condition="Report beats but stock dips >2% in first hour",
                    action="Watch for dip zone support before adding exposure; pattern favors recovery.",
                    confidence=ConfidenceTier.MEDIUM,
                    historical_basis="Dip-then-rally on prior beats",
                ),
                ActionRule(
                    condition="Report misses with gap down >3%",
                    action="Avoid catching falling knife; reassess peer spillover impact.",
                    confidence=ConfidenceTier.HIGH,
                ),
            ],
        ),
    )


def build_offline_trace(job_id: str, ticker: str) -> TraceLog:
    events = [
        make_trace_event(
            job_id,
            TraceEventType.RUN_STARTED,
            f"Playbook generation started for {ticker}",
            input_summary={"ticker": ticker},
        ),
        make_trace_event(
            job_id,
            TraceEventType.AGENT_STARTED,
            "Research agent started",
            agent_name="research",
        ),
        make_trace_event(
            job_id,
            TraceEventType.TOOL_CALL_COMPLETED,
            "tavily_search completed",
            agent_name="research",
            tool_name="tavily_search",
            latency_ms=420,
        ),
        make_trace_event(
            job_id,
            TraceEventType.AGENT_COMPLETED,
            "Research agent completed",
            agent_name="research",
            latency_ms=2100,
        ),
        make_trace_event(
            job_id,
            TraceEventType.RUN_COMPLETED,
            f"Playbook generation completed for {ticker}",
            latency_ms=1250,
        ),
    ]
    return TraceLog(
        job_id=job_id,
        ticker=ticker,
        events=events,
        total_latency_ms=1250,
    )


async def seed_live(ticker: str, store: DemoStore) -> Path:
    job_id = f"demo_{ticker.lower()}"
    orchestrator = PlaybookOrchestrator()
    playbook, trace = await orchestrator.run_with_trace(ticker, job_id=job_id)
    entry = DemoCacheEntry(
        ticker=ticker.upper(),
        job_id=job_id,
        playbook=playbook,
        trace_log=trace,
        source="live",
    )
    return store.save(entry)


async def seed_offline(ticker: str, store: DemoStore) -> Path:
    normalized = ticker.upper()
    job_id = f"demo_{normalized.lower()}"
    playbook = build_offline_playbook(normalized, job_id)
    trace = build_offline_trace(job_id, normalized)
    entry = DemoCacheEntry(
        ticker=normalized,
        job_id=job_id,
        playbook=playbook,
        trace_log=trace,
        source="offline",
    )
    return store.save(entry)


async def main() -> int:
    parser = argparse.ArgumentParser(description="Seed demo playbook cache")
    parser.add_argument(
        "--ticker",
        action="append",
        default=["AAPL"],
        help="Ticker(s) to seed (default: AAPL)",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Write mock demo data without calling external APIs",
    )
    args = parser.parse_args()

    settings = get_settings()
    store = DemoStore(settings)

    for raw_ticker in args.ticker:
        ticker = raw_ticker.upper().strip()
        if args.offline:
            path = await seed_offline(ticker, store)
            print(f"✓ Offline demo saved: {path}")
        else:
            print(f"Generating live demo for {ticker}…")
            path = await seed_live(ticker, store)
            print(f"✓ Live demo saved: {path}")

    print(f"\nAvailable demos: {', '.join(store.list_tickers())}")
    print("Load via: POST /api/playbook/demo/{ticker}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
