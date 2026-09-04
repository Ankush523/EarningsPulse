"""In-memory TTL cache for API responses."""

from __future__ import annotations

import hashlib
import json
import threading
import time
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


class TTLCache:
    """Thread-safe in-memory cache with per-key TTL."""

    def __init__(self, default_ttl_seconds: int = 300, max_entries: int = 1024):
        self._default_ttl = default_ttl_seconds
        self._max_entries = max_entries
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = threading.RLock()

    @staticmethod
    def make_key(*parts: Any) -> str:
        """Build a stable cache key from arbitrary parts."""
        payload = json.dumps(parts, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if time.monotonic() >= expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        expires_at = time.monotonic() + ttl
        with self._lock:
            if len(self._store) >= self._max_entries:
                self._evict_expired()
            if len(self._store) >= self._max_entries:
                oldest_key = next(iter(self._store))
                del self._store[oldest_key]
            self._store[key] = (expires_at, value)

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def _evict_expired(self) -> None:
        now = time.monotonic()
        expired = [k for k, (exp, _) in self._store.items() if now >= exp]
        for key in expired:
            del self._store[key]

    def get_or_set(
        self,
        key: str,
        factory: Callable[[], T],
        ttl_seconds: int | None = None,
    ) -> T:
        cached = self.get(key)
        if cached is not None:
            return cached  # type: ignore[return-value]
        value = factory()
        self.set(key, value, ttl_seconds=ttl_seconds)
        return value


# Shared application cache instance
app_cache = TTLCache(default_ttl_seconds=300)
