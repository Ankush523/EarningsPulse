"""Property tests for peer-map calculations and static taxonomy."""

from datetime import date, timedelta

import pytest
from app.models.data import OHLCVBar
from app.services.peer_map import (
    SECTOR_PEER_GROUPS,
    THEMATIC_LINKS,
    PeerMapService,
    get_static_peers,
)
from hypothesis import given, settings
from hypothesis import strategies as st

BASE_DATE = date(2024, 1, 15)
KNOWN_TICKERS = sorted(
    {
        *[ticker for members in SECTOR_PEER_GROUPS.values() for ticker in members],
        *THEMATIC_LINKS,
    }
)


def _close_bar(day_offset: int, close: int) -> OHLCVBar:
    return OHLCVBar(
        date=BASE_DATE + timedelta(days=day_offset),
        open=close,
        high=close,
        low=close,
        close=close,
    )


nonconstant_series = st.lists(
    st.integers(min_value=-1_000, max_value=1_000),
    min_size=2,
    max_size=12,
).filter(lambda values: len(set(values)) > 1)


@settings(max_examples=100, deadline=None)
@given(
    values=nonconstant_series,
    scale=st.integers(min_value=1, max_value=20),
    shift=st.integers(min_value=-1_000, max_value=1_000),
)
def test_pearson_correlation_is_affine_invariant(values, scale, shift):
    transformed = [(scale * value) + shift for value in values]

    same_direction = PeerMapService._pearson_correlation(values, transformed)
    inverse_direction = PeerMapService._pearson_correlation(
        values, [-value for value in transformed]
    )

    assert same_direction == pytest.approx(1.0, abs=1e-12)
    assert inverse_direction == pytest.approx(-1.0, abs=1e-12)


@settings(max_examples=100, deadline=None)
@given(
    x=nonconstant_series,
    data=st.data(),
)
def test_pearson_correlation_is_symmetric_and_bounded(x, data):
    y = data.draw(
        st.lists(
            st.integers(min_value=-1_000, max_value=1_000),
            min_size=len(x),
            max_size=len(x),
        ),
        label="same-length comparison series",
    )

    forward = PeerMapService._pearson_correlation(x, y)
    reverse = PeerMapService._pearson_correlation(y, x)

    assert -1.0 <= forward <= 1.0
    assert reverse == pytest.approx(forward, abs=1e-12)


@settings(max_examples=100, deadline=None)
@given(
    pre_close=st.integers(min_value=1, max_value=1_000),
    post_closes=st.lists(st.integers(min_value=1, max_value=1_000), min_size=1, max_size=7),
)
def test_earnings_window_return_uses_last_post_close(pre_close, post_closes):
    bars = [_close_bar(-1, pre_close)] + [
        _close_bar(offset, close) for offset, close in enumerate(post_closes)
    ]
    expected = ((post_closes[-1] - pre_close) / pre_close) * 100

    result = PeerMapService._earnings_window_return(bars, BASE_DATE)
    reversed_result = PeerMapService._earnings_window_return(list(reversed(bars)), BASE_DATE)

    assert result == pytest.approx(expected)
    assert reversed_result == pytest.approx(expected)


@settings(max_examples=60, deadline=None)
@given(
    ticker=st.sampled_from(KNOWN_TICKERS),
    left_padding=st.text(alphabet=" \t", max_size=3),
    right_padding=st.text(alphabet=" \t", max_size=3),
)
def test_static_peers_normalize_input_and_never_include_self(ticker, left_padding, right_padding):
    peers = get_static_peers(f"{left_padding}{ticker.lower()}{right_padding}")
    peer_tickers = [peer[0] for peer in peers]

    assert ticker not in peer_tickers
    assert len(peer_tickers) == len(set(peer_tickers))
    assert peers == get_static_peers(ticker)
