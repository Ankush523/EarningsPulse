"""Shared yfinance access with throttling, retries, and browser impersonation."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

import pandas as pd
import yfinance as yf
from curl_cffi import requests as curl_requests

logger = logging.getLogger(__name__)

_MIN_INTERVAL_SEC = 0.4
_MAX_RETRIES = 4
_RETRY_BASE_SEC = 2.0

_session: Any | None = None
_last_request = 0.0
_request_lock = threading.Lock()


def _is_rate_limit_error(exc: BaseException) -> bool:
    message = str(exc).lower()
    return "429" in message or "too many requests" in message or "rate limit" in message


def get_session() -> Any:
    """Return a shared HTTP session with Chrome impersonation."""
    global _session
    if _session is not None:
        return _session

    _session = curl_requests.Session(impersonate="chrome")
    logger.debug("yfinance session: curl_cffi chrome impersonation enabled")
    return _session


def _throttle() -> None:
    global _last_request
    with _request_lock:
        now = time.monotonic()
        elapsed = now - _last_request
        if elapsed < _MIN_INTERVAL_SEC:
            time.sleep(_MIN_INTERVAL_SEC - elapsed)
        _last_request = time.monotonic()


def get_ticker(symbol: str) -> yf.Ticker:
    """Create a rate-limited yfinance Ticker with the shared session."""
    _throttle()
    return yf.Ticker(symbol.upper().strip(), session=get_session())


def download(
    tickers: str | list[str],
    *,
    start: str | None = None,
    end: str | None = None,
    **kwargs: Any,
) -> pd.DataFrame:
    """Rate-limited yf.download wrapper (single request for multiple tickers)."""
    _throttle()
    ticker_arg = tickers if isinstance(tickers, str) else " ".join(tickers)
    return yf.download(
        ticker_arg,
        start=start,
        end=end,
        auto_adjust=True,
        progress=False,
        threads=False,
        session=get_session(),
        **kwargs,
    )


def call_with_retry(operation: str, fn: Any, *args: Any, **kwargs: Any) -> Any:
    """Run a yfinance call with exponential backoff on rate-limit errors."""
    last_exc: BaseException | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            if not _is_rate_limit_error(exc) or attempt == _MAX_RETRIES - 1:
                raise
            delay = _RETRY_BASE_SEC * (2**attempt)
            logger.warning(
                "yfinance rate limited during %s (attempt %s/%s), retrying in %.1fs",
                operation,
                attempt + 1,
                _MAX_RETRIES,
                delay,
            )
            time.sleep(delay)
    raise last_exc  # pragma: no cover
