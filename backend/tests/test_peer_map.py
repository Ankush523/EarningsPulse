"""Tests for peer map service."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.data import EarningsEvent, HistoricalEarningsResponse, OHLCVBar
from app.models.playbook import PeerRelationship
from app.services.earnings_calendar import EarningsCalendarService
from app.services.peer_map import (
    PeerMapService,
    find_groups_for_ticker,
    get_static_peers,
)
from app.services.price_data import PriceDataService


def test_find_groups_for_ticker():
    groups = find_groups_for_ticker("NVDA")
    assert "semiconductors" in groups
    assert "ai_infrastructure" in groups


def test_get_static_peers_nvda():
    peers = get_static_peers("NVDA")
    tickers = {p[0] for p in peers}
    assert "AMD" in tickers
    assert "NVDA" not in tickers


def test_get_static_peers_includes_thematic_links():
    peers = get_static_peers("NVDA")
    mu = next(p for p in peers if p[0] == "MU")
    assert mu[1] == PeerRelationship.SUPPLIER


def test_pearson_correlation():
    score = PeerMapService._pearson_correlation([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])
    assert score == pytest.approx(1.0)


def test_direction_from_score():
    assert PeerMapService._direction_from_score(0.6) == "same"
    assert PeerMapService._direction_from_score(-0.5) == "inverse"
    assert PeerMapService._direction_from_score(0.1) == "weak"


@pytest.mark.asyncio
async def test_build_peer_map(settings, cache):
    earnings_service = EarningsCalendarService(settings=settings, cache=cache)
    earnings_service.get_historical_earnings = AsyncMock(
        return_value=HistoricalEarningsResponse(
            ticker="NVDA",
            source="finnhub",
            events=[
                EarningsEvent(ticker="NVDA", report_date=date(2024, 5, 22)),
                EarningsEvent(ticker="NVDA", report_date=date(2024, 2, 21)),
            ],
        )
    )

    def mock_fetch(ticker, start, end, **kwargs):
        days = (end - start).days + 1
        bars = [
            OHLCVBar(
                date=date.fromordinal(start.toordinal() + i),
                open=100 + i,
                high=101 + i,
                low=99 + i,
                close=100 + i,
            )
            for i in range(max(days, 1))
        ]
        return bars

    price_service = PriceDataService(cache=cache)
    price_service.fetch_ohlcv = MagicMock(side_effect=mock_fetch)
    price_service.get_company_name = MagicMock(return_value="Mock Co")

    service = PeerMapService(
        price_service=price_service,
        earnings_service=earnings_service,
        cache=cache,
    )

    result = await service.build_peer_map("NVDA", max_peers=5, use_cache=False)

    assert result.reporting_ticker == "NVDA"
    assert len(result.peers) <= 5
    assert all(-1 <= peer.correlation_score <= 1 for peer in result.peers)
    assert result.peers[0].ticker != "NVDA"
