"""Tests for reaction analyzer."""

from datetime import date

import pytest
from app.models.data import EarningsEvent, OHLCVBar
from app.models.playbook import ReactionArchetype, ReportOutcome
from app.services.reaction_analyzer import ReactionAnalyzer


def _bars_dip_then_rally() -> list[OHLCVBar]:
    return [
        OHLCVBar(date=date(2024, 1, 2), open=100, high=101, low=99, close=100),
        OHLCVBar(date=date(2024, 1, 3), open=100, high=101, low=94, close=95),
        OHLCVBar(date=date(2024, 1, 4), open=95, high=110, low=95, close=108),
        OHLCVBar(date=date(2024, 1, 5), open=108, high=112, low=107, close=111),
    ]


def _bars_immediate_rip() -> list[OHLCVBar]:
    return [
        OHLCVBar(date=date(2024, 2, 2), open=50, high=51, low=49, close=50),
        OHLCVBar(date=date(2024, 2, 3), open=50, high=56, low=50, close=55),
        OHLCVBar(date=date(2024, 2, 4), open=55, high=58, low=54, close=57),
    ]


def _bars_gap_and_hold() -> list[OHLCVBar]:
    return [
        OHLCVBar(date=date(2024, 3, 2), open=80, high=81, low=79, close=80),
        OHLCVBar(date=date(2024, 3, 3), open=80, high=80, low=72, close=73),
        OHLCVBar(date=date(2024, 3, 4), open=73, high=74, low=70, close=71),
    ]


def test_classify_dip_then_rally():
    pattern = ReactionAnalyzer.classify_single_reaction(
        outcome=ReportOutcome.BEAT,
        initial_move_pct=-5.0,
        dip_pct=-6.0,
        recovery_pct=11.0,
    )
    assert pattern == ReactionArchetype.DIP_THEN_RALLY


def test_classify_immediate_rip():
    pattern = ReactionAnalyzer.classify_single_reaction(
        outcome=ReportOutcome.BEAT,
        initial_move_pct=10.0,
        dip_pct=-0.2,
        recovery_pct=10.0,
    )
    assert pattern == ReactionArchetype.IMMEDIATE_RIP


def test_classify_gap_and_hold():
    pattern = ReactionAnalyzer.classify_single_reaction(
        outcome=ReportOutcome.MISS,
        initial_move_pct=-8.75,
        dip_pct=-10.0,
        recovery_pct=-8.0,
    )
    assert pattern == ReactionArchetype.GAP_AND_HOLD


def test_analyze_window_dip_then_rally():
    analyzer = ReactionAnalyzer()
    event = analyzer.analyze_window(
        "NVDA",
        date(2024, 1, 3),
        _bars_dip_then_rally(),
        report_outcome=ReportOutcome.BEAT,
    )
    assert event is not None
    assert event.pattern == ReactionArchetype.DIP_THEN_RALLY
    assert event.dip_pct is not None
    assert event.dip_pct < 0
    assert event.recovery_pct is not None
    assert event.recovery_pct > 0


def test_analyze_window_immediate_rip():
    analyzer = ReactionAnalyzer()
    event = analyzer.analyze_window(
        "AAPL",
        date(2024, 2, 3),
        _bars_immediate_rip(),
        report_outcome=ReportOutcome.BEAT,
    )
    assert event is not None
    assert event.pattern == ReactionArchetype.IMMEDIATE_RIP


def test_aggregate_events():
    analyzer = ReactionAnalyzer()
    events = [
        analyzer.analyze_window(
            "TSLA",
            date(2024, 1, 3),
            _bars_dip_then_rally(),
            report_outcome=ReportOutcome.BEAT,
        ),
        analyzer.analyze_window(
            "TSLA",
            date(2024, 2, 3),
            _bars_immediate_rip(),
            report_outcome=ReportOutcome.BEAT,
        ),
    ]
    events = [e for e in events if e is not None]
    analysis = analyzer.aggregate_events("TSLA", events)

    assert analysis.events_analyzed == 2
    assert analysis.archetype in {
        ReactionArchetype.DIP_THEN_RALLY,
        ReactionArchetype.IMMEDIATE_RIP,
    }
    assert analysis.pattern_counts


def test_aggregate_empty_events():
    analysis = ReactionAnalyzer().aggregate_events("XYZ", [])
    assert analysis.archetype == ReactionArchetype.INSUFFICIENT_DATA
    assert analysis.events_analyzed == 0


@pytest.mark.asyncio
async def test_analyze_ticker_with_mocks(settings, cache):
    from unittest.mock import AsyncMock, MagicMock

    from app.models.data import EarningsWindowPrices, HistoricalEarningsResponse
    from app.services.earnings_calendar import EarningsCalendarService
    from app.services.price_data import PriceDataService

    earnings_service = EarningsCalendarService(settings=settings, cache=cache)
    earnings_service.get_historical_earnings = AsyncMock(
        return_value=HistoricalEarningsResponse(
            ticker="AAPL",
            source="finnhub",
            events=[
                EarningsEvent(
                    ticker="AAPL", report_date=date(2024, 1, 3), eps_estimate=1.0, eps_actual=1.2
                ),
            ],
        )
    )

    price_service = PriceDataService(cache=cache)
    dip_bars = _bars_dip_then_rally()
    price_service.fetch_ohlcv = MagicMock(return_value=dip_bars)
    price_service.fetch_around_earnings = MagicMock(
        return_value=EarningsWindowPrices(
            ticker="AAPL",
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
    result = await analyzer.analyze_ticker("AAPL", limit=1, use_cache=False)

    assert result.ticker == "AAPL"
    assert result.events_analyzed == 1
    assert result.archetype == ReactionArchetype.DIP_THEN_RALLY


def test_aggregate_with_options_implied_move_overpriced():
    from app.models.analysis import EarningsReactionEvent

    analyzer = ReactionAnalyzer()
    events = [
        EarningsReactionEvent(
            ticker="AAPL",
            earnings_date=date(2024, 1, 3),
            report_outcome=ReportOutcome.BEAT,
            initial_move_pct=3.0,
            dip_pct=-2.0,
            recovery_pct=5.0,
            pattern=ReactionArchetype.DIP_THEN_RALLY,
        ),
        EarningsReactionEvent(
            ticker="AAPL",
            earnings_date=date(2023, 10, 3),
            report_outcome=ReportOutcome.BEAT,
            initial_move_pct=-3.0,
            dip_pct=-3.5,
            recovery_pct=4.0,
            pattern=ReactionArchetype.DIP_THEN_RALLY,
        ),
    ]
    options_data = {
        "implied_move_pct": 5.5,
        "atm_strike": 150.0,
    }
    result = analyzer.aggregate_events("AAPL", events, options_data=options_data)
    assert result.historical_move_pct == 3.0
    assert result.implied_move_pct == 5.5
    assert result.volatility_assessment == "OVERPRICED"
    assert result.options_summary is not None
    assert "volatility overpriced" in result.options_summary


def test_aggregate_with_options_implied_move_underpriced():
    from app.models.analysis import EarningsReactionEvent

    analyzer = ReactionAnalyzer()
    events = [
        EarningsReactionEvent(
            ticker="AAPL",
            earnings_date=date(2024, 1, 3),
            report_outcome=ReportOutcome.BEAT,
            initial_move_pct=6.0,
            pattern=ReactionArchetype.IMMEDIATE_RIP,
        ),
    ]
    options_data = {
        "implied_move_pct": 3.0,
    }
    result = analyzer.aggregate_events("AAPL", events, options_data=options_data)
    assert result.historical_move_pct == 6.0
    assert result.implied_move_pct == 3.0
    assert result.volatility_assessment == "UNDERPRICED"
    assert result.options_summary is not None
    assert "volatility underpriced" in result.options_summary
