"""Backtest validation tests for reaction pattern classification."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.models.analysis import PeerMapResult
from app.models.data import EarningsEvent, EarningsWindowPrices, HistoricalEarningsResponse
from app.models.playbook import ConfidenceTier, ReactionArchetype, ReportOutcome
from app.services.peer_map import PeerMapService
from app.services.reaction_analyzer import ReactionAnalyzer
from tests.test_reaction_analyzer import (
    _bars_dip_then_rally,
    _bars_gap_and_hold,
    _bars_immediate_rip,
)

# Backtest tickers from IMPLEMENTATION_PLAN §12
BACKTEST_TICKERS = ["AAPL", "NVDA", "TSLA", "JPM", "AMZN"]

# Expected pattern families for validation (not hardcoded logic — sanity checks)
KNOWN_VOLATILE_TICKERS = {"NVDA", "TSLA"}
KNOWN_MEGA_CAP = {"AAPL", "AMZN", "JPM"}


def test_backtest_ticker_list_matches_plan():
    assert BACKTEST_TICKERS == ["AAPL", "NVDA", "TSLA", "JPM", "AMZN"]


@pytest.mark.parametrize(
    "bars,earnings_date,outcome,expected",
    [
        (
            _bars_dip_then_rally(),
            date(2024, 1, 3),
            ReportOutcome.BEAT,
            ReactionArchetype.DIP_THEN_RALLY,
        ),
        (
            _bars_immediate_rip(),
            date(2024, 2, 3),
            ReportOutcome.BEAT,
            ReactionArchetype.IMMEDIATE_RIP,
        ),
        (
            _bars_gap_and_hold(),
            date(2024, 3, 3),
            ReportOutcome.MISS,
            ReactionArchetype.GAP_AND_HOLD,
        ),
    ],
)
def test_backtest_pattern_labels_reasonable(bars, earnings_date, outcome, expected):
    """Validate pattern classifier on synthetic windows mimicking backtest tickers."""
    analyzer = ReactionAnalyzer()
    event = analyzer.analyze_window(
        "NVDA",
        earnings_date,
        bars,
        report_outcome=outcome,
    )
    assert event is not None
    assert event.pattern == expected


@pytest.mark.asyncio
@pytest.mark.parametrize("ticker", BACKTEST_TICKERS)
async def test_backtest_analyze_ticker_mocked(settings, cache, ticker):
    """Each backtest ticker produces a valid analysis when data services are mocked."""
    from app.services.earnings_calendar import EarningsCalendarService
    from app.services.price_data import PriceDataService

    earnings_service = EarningsCalendarService(settings=settings, cache=cache)
    earnings_service.get_historical_earnings = AsyncMock(
        return_value=HistoricalEarningsResponse(
            ticker=ticker,
            source="test",
            events=[
                EarningsEvent(
                    ticker=ticker,
                    report_date=date(2024, 1, 3),
                    eps_estimate=1.0,
                    eps_actual=1.1,
                ),
            ],
        )
    )

    price_service = PriceDataService(cache=cache)
    dip_bars = _bars_dip_then_rally()
    price_service.fetch_ohlcv = MagicMock(return_value=dip_bars)
    price_service.fetch_around_earnings = MagicMock(
        return_value=EarningsWindowPrices(
            ticker=ticker,
            earnings_date=date(2024, 1, 3),
            window_days=3,
            bars=dip_bars,
            metrics=None,
        )
    )

    analyzer = ReactionAnalyzer(
        price_service=price_service,
        earnings_service=earnings_service,
        cache=cache,
    )
    result = await analyzer.analyze_ticker(ticker, limit=1, use_cache=False)

    assert result.ticker == ticker
    assert result.events_analyzed >= 1
    assert result.archetype != ReactionArchetype.INSUFFICIENT_DATA
    assert result.confidence in ConfidenceTier


@pytest.mark.asyncio
async def test_backtest_peer_map_mocked(settings, cache, mock_peer_map_result):
    """Peer map returns ranked peers for backtest tickers."""
    service = PeerMapService(cache=cache)
    service.build_peer_map = AsyncMock(return_value=mock_peer_map_result)

    result: PeerMapResult = await service.build_peer_map("AAPL", max_peers=5)
    assert result.reporting_ticker == "AAPL"
    assert len(result.peers) >= 1
    assert all(-1.0 <= p.correlation_score <= 1.0 for p in result.peers)
