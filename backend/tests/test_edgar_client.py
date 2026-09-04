"""Tests for SEC EDGAR client."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from app.models.data import FilingType
from app.services.edgar_client import EdgarClient
from app.services.errors import DataNotFoundError


@pytest.mark.asyncio
async def test_get_filings(settings, cache):
    ticker_map_response = MagicMock()
    ticker_map_response.raise_for_status = MagicMock()
    ticker_map_response.json.return_value = {
        "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}
    }

    submissions_response = MagicMock()
    submissions_response.raise_for_status = MagicMock()
    submissions_response.json.return_value = {
        "filings": {
            "recent": {
                "form": ["10-Q", "10-K", "8-K"],
                "filingDate": ["2024-08-01", "2023-11-03", "2024-05-02"],
                "accessionNumber": [
                    "0000320193-24-000123",
                    "0000320193-23-000106",
                    "0000320193-24-000050",
                ],
                "primaryDocument": [
                    "aapl-20240629.htm",
                    "aapl-20230930.htm",
                    "aapl-8k.htm",
                ],
                "reportDate": ["2024-06-29", "2023-09-30", "2024-05-02"],
            }
        }
    }

    mock_client = AsyncMock()

    async def mock_get(url, *args, **kwargs):
        if "company_tickers.json" in url:
            return ticker_map_response
        return submissions_response

    mock_client.get = AsyncMock(side_effect=mock_get)

    client = EdgarClient(settings=settings, cache=cache, client=mock_client)
    result = await client.get_filings("AAPL")

    assert result.ticker == "AAPL"
    assert result.company_name == "Apple Inc."
    assert result.latest_quarterly is not None
    assert result.latest_quarterly.form_type == FilingType.TEN_Q
    assert result.latest_annual is not None
    assert result.latest_annual.form_type == FilingType.TEN_K
    assert len(result.recent_filings) >= 2


@pytest.mark.asyncio
async def test_get_filings_unknown_ticker(settings, cache):
    ticker_map_response = MagicMock()
    ticker_map_response.raise_for_status = MagicMock()
    ticker_map_response.json.return_value = {}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=ticker_map_response)

    client = EdgarClient(settings=settings, cache=cache, client=mock_client)

    with pytest.raises(DataNotFoundError):
        await client.get_filings("UNKNOWN")
