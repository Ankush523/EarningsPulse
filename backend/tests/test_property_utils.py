"""Property-based checks for pure confidence and cache utilities."""

from __future__ import annotations

import re
from unittest.mock import patch

from app.models.playbook import ConfidenceTier
from app.utils.cache import TTLCache
from app.utils.confidence import combine_confidence, score_from_sample_size
from hypothesis import given, settings
from hypothesis import strategies as st

TIER_RANK = {
    ConfidenceTier.LOW: 1,
    ConfidenceTier.MEDIUM: 2,
    ConfidenceTier.HIGH: 3,
}


@settings(max_examples=80)
@given(
    medium_threshold=st.integers(min_value=-20, max_value=100),
    threshold_gap=st.integers(min_value=0, max_value=100),
    first=st.integers(min_value=-100, max_value=200),
    increase=st.integers(min_value=0, max_value=200),
)
def test_sample_size_confidence_is_monotone(
    medium_threshold: int,
    threshold_gap: int,
    first: int,
    increase: int,
) -> None:
    high_threshold = medium_threshold + threshold_gap
    second = first + increase

    first_tier = score_from_sample_size(
        first,
        high_threshold=high_threshold,
        medium_threshold=medium_threshold,
    )
    second_tier = score_from_sample_size(
        second,
        high_threshold=high_threshold,
        medium_threshold=medium_threshold,
    )

    assert TIER_RANK[first_tier] <= TIER_RANK[second_tier]


@settings(max_examples=50)
@given(st.lists(st.sampled_from(list(ConfidenceTier)), min_size=1, max_size=12))
def test_combine_confidence_is_order_independent_and_conservative(
    tiers: list[ConfidenceTier],
) -> None:
    combined = combine_confidence(*tiers)

    assert combine_confidence(*reversed(tiers)) == combined
    assert combined in tiers
    assert combine_confidence(combined, ConfidenceTier.HIGH) == combined
    assert combine_confidence(combined, ConfidenceTier.LOW) == ConfidenceTier.LOW


cache_key_values = st.dictionaries(
    st.text(min_size=1, max_size=12),
    st.one_of(
        st.none(),
        st.booleans(),
        st.integers(min_value=-(2**31), max_value=2**31 - 1),
        st.text(max_size=20),
    ),
    max_size=8,
)


@settings(max_examples=50)
@given(cache_key_values)
def test_cache_key_is_independent_of_mapping_insertion_order(
    values: dict[str, object],
) -> None:
    reversed_values = dict(reversed(list(values.items())))

    original_key = TTLCache.make_key(values)
    reordered_key = TTLCache.make_key(reversed_values)

    assert original_key == reordered_key
    assert re.fullmatch(r"[0-9a-f]{64}", original_key)


@settings(max_examples=60)
@given(
    keys=st.lists(st.text(min_size=1, max_size=12), min_size=1, max_size=20, unique=True),
    max_entries=st.integers(min_value=1, max_value=10),
)
def test_cache_never_exceeds_capacity_and_keeps_newest_entries(
    keys: list[str],
    max_entries: int,
) -> None:
    cache = TTLCache(default_ttl_seconds=60, max_entries=max_entries)

    for index, key in enumerate(keys):
        cache.set(key, index)

    retained = keys[-max_entries:]
    assert len(cache._store) <= max_entries
    assert [cache.get(key) for key in retained] == list(range(len(keys) - len(retained), len(keys)))


@settings(max_examples=40)
@given(
    ttl=st.integers(min_value=1, max_value=1_000_000),
    before_expiry=st.integers(min_value=0, max_value=999_999),
)
def test_cache_expiry_boundary_uses_monotonic_time(
    ttl: int,
    before_expiry: int,
) -> None:
    now = 10_000_000
    with patch("app.utils.cache.time.monotonic", side_effect=lambda: now):
        cache = TTLCache(default_ttl_seconds=ttl)
        cache.set("key", "value")

        now += min(before_expiry, ttl - 1)
        assert cache.get("key") == "value"

        now = 10_000_000 + ttl
        assert cache.get("key") is None
