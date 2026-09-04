"""Tests for price data service."""

from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from app.models.data import OHLCVBar
from app.services.errors import DataNotFoundError
from app.services.price_data import PriceDataService


def test_fetch_ohlcv_returns_bars(cache, sample_price_history):
    service = PriceDataService(cache=cache)
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = sample_price_history

    with patch("app.services.price_data.get_ticker", return_value=mock_ticker):
        bars = service.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 1, 5))

    assert len(bars) == 5
    assert bars[0].close == 101.0
    assert bars[-1].date == date(2024, 1, 5)


def test_fetch_ohlcv_uses_cache(cache, sample_price_history):
    service = PriceDataService(cache=cache)
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = sample_price_history

    with patch("app.services.price_data.get_ticker", return_value=mock_ticker):
        first = service.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 1, 5))
        second = service.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 1, 5))

    assert first == second
    mock_ticker.history.assert_called_once()


def test_fetch_ohlcv_empty_raises(cache):
    service = PriceDataService(cache=cache)
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = pd.DataFrame()

    with patch("app.services.price_data.get_ticker", return_value=mock_ticker):
        with pytest.raises(DataNotFoundError):
            service.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 1, 5))


def test_fetch_around_earnings(cache, sample_price_history, earnings_date):
    service = PriceDataService(cache=cache)
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = sample_price_history

    with patch("app.services.price_data.get_ticker", return_value=mock_ticker):
        window = service.fetch_around_earnings("AAPL", earnings_date, window_days=2)

    assert window.ticker == "AAPL"
    assert window.earnings_date == earnings_date
    assert window.metrics is not None
    assert window.metrics.total_return_pct != 0


def test_calculate_window_metrics():
    bars = [
        OHLCVBar(date=date(2024, 1, 1), open=100, high=102, low=99, close=100),
        OHLCVBar(date=date(2024, 1, 2), open=100, high=110, low=95, close=105),
    ]
    metrics = PriceDataService.calculate_window_metrics(bars)
    assert metrics is not None
    assert metrics.total_return_pct == 5.0
    assert metrics.max_drawdown_pct == -5.0
    assert metrics.max_gain_pct == 10.0


def test_calculate_dip_recovery():
    bars = [
        OHLCVBar(date=date(2024, 1, 2), open=100, high=101, low=99, close=100),
        OHLCVBar(date=date(2024, 1, 3), open=100, high=101, low=95, close=96),
        OHLCVBar(date=date(2024, 1, 4), open=96, high=108, low=96, close=107),
    ]
    result = PriceDataService().calculate_dip_recovery(bars, date(2024, 1, 3))
    assert result["baseline_price"] == 100
    assert result["dip_pct"] == -5.0
    assert result["recovery_pct"] == 8.0
