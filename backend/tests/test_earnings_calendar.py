"""Tests for earnings calendar service."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest
from app.config import Settings
from app.services.earnings_calendar import EarningsCalendarService
from app.services.errors import ConfigurationError, DataNotFoundError


@pytest.mark.asyncio
async def test_get_upcoming_earnings(settings, cache):
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "earningsCalendar": [
            {
                "symbol": "AAPL",
                "date": "2025-09-10",
                "hour": "amc",
                "epsEstimate": 1.25,
                "quarter": 3,
                "year": 2025,
            }
        ]
    }

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    service = EarningsCalendarService(
        settings=settings,
        cache=cache,
        client=mock_client,
    )

    result = await service.get_upcoming_earnings(days=7)

    assert result.events[0].ticker == "AAPL"
    assert result.events[0].report_time == "amc"
    assert result.from_date <= result.to_date


@pytest.mark.asyncio
async def test_get_upcoming_earnings_requires_api_key(cache):
    settings = Settings(finnhub_api_key=None)
    service = EarningsCalendarService(settings=settings, cache=cache)

    with pytest.raises(ConfigurationError):
        await service.get_upcoming_earnings()


@pytest.mark.asyncio
async def test_get_peers_from_finnhub(settings, cache):
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = ["AAPL", "DELL", "HPQ", "HPE"]

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    service = EarningsCalendarService(
        settings=settings,
        cache=cache,
        client=mock_client,
    )
    peers = await service.get_peers("AAPL", use_cache=False)
    assert "AAPL" not in peers
    assert "DELL" in peers
    assert "HPQ" in peers


@pytest.mark.asyncio
async def test_get_historical_earnings_from_finnhub(settings, cache):
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = [
        {
            "period": "2024-06-30",
            "actual": 1.4,
            "estimate": 1.35,
        },
        {
            "period": "2024-03-31",
            "actual": 1.2,
            "estimate": 1.18,
        },
    ]

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    service = EarningsCalendarService(
        settings=settings,
        cache=cache,
        client=mock_client,
    )

    with patch.object(
        service,
        "_fetch_historical_from_yfinance",
        side_effect=DataNotFoundError("missing", service="yfinance"),
    ):
        result = await service.get_historical_earnings("AAPL", limit=8)

    assert result.ticker == "AAPL"
    assert result.source == "finnhub"
    assert len(result.events) == 2
    assert result.events[0].report_date == date(2024, 6, 30)


@pytest.mark.asyncio
async def test_get_historical_earnings_finnhub_fallback(settings, cache):
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = [
        {
            "period": "2024-06-30",
            "actual": 1.4,
            "estimate": 1.35,
        },
    ]

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    service = EarningsCalendarService(
        settings=settings,
        cache=cache,
        client=mock_client,
    )

    with patch.object(
        service,
        "_fetch_historical_from_yfinance",
        side_effect=DataNotFoundError("missing", service="yfinance"),
    ):
        result = await service.get_historical_earnings("AAPL", limit=8)

    assert result.source == "finnhub"
    assert result.events[0].report_date == date(2024, 6, 30)


@pytest.mark.asyncio
async def test_get_historical_earnings_from_yfinance(settings, cache):
    earnings_df = pd.DataFrame(
        {
            "EPS Estimate": [1.2],
            "Reported EPS": [1.25],
            "Hour": ["After Market Close"],
        },
        index=pd.to_datetime(["2024-06-30"]),
    )

    mock_ticker = MagicMock()
    mock_ticker.earnings_dates = earnings_df

    service = EarningsCalendarService(settings=settings, cache=cache)

    with (
        patch("app.services.earnings_calendar.get_ticker", return_value=mock_ticker),
        patch(
            "app.services.earnings_calendar.call_with_retry",
            side_effect=lambda _op, fn, *args, **kwargs: fn(*args, **kwargs),
        ),
    ):
        result = await service.get_historical_earnings("AAPL", limit=8)

    assert result.source == "yfinance"
    assert result.events[0].report_time == "amc"


@pytest.mark.asyncio
async def test_get_next_earnings_date(settings, cache):
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "earningsCalendar": [
            {"symbol": "AAPL", "date": "2025-09-10", "hour": "amc"},
            {"symbol": "MSFT", "date": "2025-09-11", "hour": "amc"},
        ]
    }

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    service = EarningsCalendarService(
        settings=settings,
        cache=cache,
        client=mock_client,
    )

    next_date = await service.get_next_earnings_date("AAPL")
    assert next_date == date(2025, 9, 10)
