"""Tests for shared yfinance client helpers."""

from unittest.mock import MagicMock, patch

import pytest
from app.services import yfinance_client


def test_is_rate_limit_error_detects_429():
    assert yfinance_client._is_rate_limit_error(Exception("429 Client Error"))
    assert yfinance_client._is_rate_limit_error(Exception("Too Many Requests"))


def test_call_with_retry_succeeds_on_second_attempt():
    calls = {"count": 0}

    def flaky():
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("429 Too Many Requests")
        return "ok"

    with patch("app.services.yfinance_client.time.sleep"):
        result = yfinance_client.call_with_retry("test", flaky)

    assert result == "ok"
    assert calls["count"] == 2


def test_call_with_retry_raises_non_rate_limit_immediately():
    def fail():
        raise ValueError("bad")

    with pytest.raises(ValueError):
        yfinance_client.call_with_retry("test", fail)


def test_get_session_uses_curl_cffi_chrome_impersonation():
    with patch.object(yfinance_client, "curl_requests") as mock_curl:
        mock_curl.Session.return_value = MagicMock()
        yfinance_client._session = None
        session = yfinance_client.get_session()
        mock_curl.Session.assert_called_once_with(impersonate="chrome")
        assert session is mock_curl.Session.return_value
