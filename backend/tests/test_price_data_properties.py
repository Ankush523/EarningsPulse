"""Property tests for deterministic price-window calculations."""

from datetime import date, timedelta

import pytest
from app.models.data import OHLCVBar
from app.services.price_data import PriceDataService
from hypothesis import given, settings
from hypothesis import strategies as st

BASE_DATE = date(2024, 1, 15)


def _bar(day_offset: int, close: int, low_offset: int, high_offset: int) -> OHLCVBar:
    low = max(1, close - low_offset)
    high = close + high_offset
    return OHLCVBar(
        date=BASE_DATE + timedelta(days=day_offset),
        open=close,
        high=high,
        low=low,
        close=close,
    )


@st.composite
def price_windows(draw: st.DrawFn) -> list[OHLCVBar]:
    offsets = draw(
        st.lists(
            st.integers(min_value=-10, max_value=10),
            min_size=2,
            max_size=10,
            unique=True,
        )
    )
    closes = draw(
        st.lists(
            st.integers(min_value=10, max_value=1_000),
            min_size=len(offsets),
            max_size=len(offsets),
        )
    )
    low_offsets = draw(
        st.lists(
            st.integers(min_value=0, max_value=9),
            min_size=len(offsets),
            max_size=len(offsets),
        )
    )
    high_offsets = draw(
        st.lists(
            st.integers(min_value=0, max_value=9),
            min_size=len(offsets),
            max_size=len(offsets),
        )
    )
    return [
        _bar(offset, close, low_offset, high_offset)
        for offset, close, low_offset, high_offset in zip(
            offsets, closes, low_offsets, high_offsets, strict=True
        )
    ]


@st.composite
def earnings_windows(draw: st.DrawFn) -> list[OHLCVBar]:
    extra_offsets = draw(
        st.lists(
            st.integers(min_value=-7, max_value=7).filter(lambda offset: offset not in {-1, 0}),
            max_size=8,
            unique=True,
        )
    )
    offsets = [-1, 0, *extra_offsets]
    closes = draw(
        st.lists(
            st.integers(min_value=10, max_value=1_000),
            min_size=len(offsets),
            max_size=len(offsets),
        )
    )
    low_offsets = draw(
        st.lists(
            st.integers(min_value=0, max_value=9),
            min_size=len(offsets),
            max_size=len(offsets),
        )
    )
    high_offsets = draw(
        st.lists(
            st.integers(min_value=0, max_value=9),
            min_size=len(offsets),
            max_size=len(offsets),
        )
    )
    return [
        _bar(offset, close, low_offset, high_offset)
        for offset, close, low_offset, high_offset in zip(
            offsets, closes, low_offsets, high_offsets, strict=True
        )
    ]


@settings(max_examples=100, deadline=None)
@given(price_windows())
def test_window_metrics_match_direct_calculation_regardless_of_input_order(bars):
    ordered = sorted(bars, key=lambda bar: bar.date)
    start = ordered[0].close
    end = ordered[-1].close
    expected = {
        "start_price": start,
        "end_price": end,
        "high_price": max(bar.high for bar in ordered),
        "low_price": min(bar.low for bar in ordered),
        "total_return_pct": round(((end - start) / start) * 100, 4),
        "max_drawdown_pct": round(((min(bar.low for bar in ordered) - start) / start) * 100, 4),
        "max_gain_pct": round(((max(bar.high for bar in ordered) - start) / start) * 100, 4),
    }

    metrics = PriceDataService.calculate_window_metrics(bars)
    reversed_metrics = PriceDataService.calculate_window_metrics(list(reversed(bars)))

    assert metrics is not None
    assert reversed_metrics == metrics
    for field, value in expected.items():
        assert getattr(metrics, field) == pytest.approx(value)


@settings(max_examples=100, deadline=None)
@given(earnings_windows())
def test_dip_recovery_uses_latest_pre_earnings_close_and_post_extrema(bars):
    ordered = sorted(bars, key=lambda bar: bar.date)
    baseline = [bar for bar in ordered if bar.date < BASE_DATE][-1].close
    post = [bar for bar in ordered if bar.date >= BASE_DATE]
    expected_dip = round(((min(bar.low for bar in post) - baseline) / baseline) * 100, 4)
    expected_recovery = round(((max(bar.high for bar in post) - baseline) / baseline) * 100, 4)

    result = PriceDataService().calculate_dip_recovery(bars, BASE_DATE)
    reversed_result = PriceDataService().calculate_dip_recovery(list(reversed(bars)), BASE_DATE)

    assert reversed_result == result
    assert result["baseline_price"] == baseline
    assert result["dip_pct"] == pytest.approx(expected_dip)
    assert result["recovery_pct"] == pytest.approx(expected_recovery)
