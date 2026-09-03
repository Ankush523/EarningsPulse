"""Tests for TTL cache."""

import time

from app.utils.cache import TTLCache


def test_cache_set_and_get():
    cache = TTLCache(default_ttl_seconds=60)
    cache.set("key", {"value": 1})
    assert cache.get("key") == {"value": 1}


def test_cache_expires():
    cache = TTLCache(default_ttl_seconds=1)
    cache.set("key", "value", ttl_seconds=1)
    assert cache.get("key") == "value"
    time.sleep(1.1)
    assert cache.get("key") is None


def test_cache_get_or_set():
    cache = TTLCache(default_ttl_seconds=60)
    calls = {"count": 0}

    def factory():
        calls["count"] += 1
        return "computed"

    first = cache.get_or_set("key", factory)
    second = cache.get_or_set("key", factory)

    assert first == "computed"
    assert second == "computed"
    assert calls["count"] == 1


def test_cache_make_key_is_stable():
    key_a = TTLCache.make_key("a", 1, {"b": 2})
    key_b = TTLCache.make_key("a", 1, {"b": 2})
    key_c = TTLCache.make_key("a", 1, {"b": 3})
    assert key_a == key_b
    assert key_a != key_c
