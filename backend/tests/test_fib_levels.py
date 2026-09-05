"""Tests for Fibonacci retracement helpers."""

from datetime import date

from app.models.data import OHLCVBar
from app.services.price_data import PriceDataService


def _bar(day: int, *, high: float, low: float, close: float) -> OHLCVBar:
    return OHLCVBar(
        date=date(2024, 1, day),
        open=close,
        high=high,
        low=low,
        close=close,
        volume=1_000_000,
    )


def test_compute_fib_retracement_levels():
    bars = [
        _bar(i, high=110 + i * 0.2, low=90 + i * 0.1, close=100 + i * 0.15) for i in range(1, 25)
    ]
    earnings_date = date(2024, 1, 24)
    levels = PriceDataService.compute_fib_retracement(bars, earnings_date)

    assert "fib_0.382" in levels
    assert "fib_0.618" in levels
    assert levels["swing_high"] >= levels["swing_low"]
    assert "fib_0.382_pct" in levels


def test_slice_window_bars():
    bars = [_bar(i, high=100, low=99, close=99.5) for i in range(1, 15)]
    window = PriceDataService.slice_window_bars(bars, date(2024, 1, 10), window_days=2)
    assert window
    assert min(bar.date for bar in window) >= date(2024, 1, 8)
    assert max(bar.date for bar in window) <= date(2024, 1, 12)
