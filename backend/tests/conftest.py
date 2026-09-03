"""Shared pytest fixtures."""

from datetime import date

import pandas as pd
import pytest

from app.config import Settings
from app.utils.cache import TTLCache


@pytest.fixture
def settings() -> Settings:
    return Settings(
        finnhub_api_key="test-finnhub-key",
        tavily_api_key="test-tavily-key",
        sec_user_agent="EarningsPulse test@example.com",
    )


@pytest.fixture
def cache() -> TTLCache:
    return TTLCache(default_ttl_seconds=60, max_entries=128)


@pytest.fixture
def sample_price_history() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Open": [100.0, 101.0, 99.0, 103.0, 105.0],
            "High": [102.0, 103.0, 100.0, 106.0, 108.0],
            "Low": [99.0, 100.0, 97.0, 101.0, 104.0],
            "Close": [101.0, 102.0, 98.0, 105.0, 107.0],
            "Volume": [1_000_000, 1_100_000, 1_200_000, 1_300_000, 1_400_000],
        },
        index=pd.to_datetime(
            ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]
        ),
    )


@pytest.fixture
def earnings_date() -> date:
    return date(2024, 1, 3)
