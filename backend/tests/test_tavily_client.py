"""Tests for Tavily client."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from app.services.errors import ConfigurationError
from app.services.tavily_client import TavilyClient


@pytest.mark.asyncio
async def test_search_returns_results(settings, cache):
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {
                "title": "AAPL earnings preview",
                "url": "https://example.com/aapl",
                "content": "Apple is expected to beat estimates.",
                "score": 0.91,
            }
        ],
        "answer": "Apple may beat on services revenue.",
        "response_time": 1.2,
    }

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    client = TavilyClient(settings=settings, cache=cache, client=mock_client)
    result = await client.search("AAPL earnings preview")

    assert result.query == "AAPL earnings preview"
    assert len(result.results) == 1
    assert result.results[0].url == "https://example.com/aapl"
    assert result.answer is not None


@pytest.mark.asyncio
async def test_search_requires_api_key(cache):
    from app.config import Settings

    settings = Settings(tavily_api_key=None)
    client = TavilyClient(settings=settings, cache=cache)

    with pytest.raises(ConfigurationError):
        await client.search("AAPL news")


@pytest.mark.asyncio
async def test_search_company_news(settings, cache):
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"results": [], "answer": None}

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    client = TavilyClient(settings=settings, cache=cache, client=mock_client)
    result = await client.search_company_news("AAPL", "Apple Inc.", days=90)

    assert "AAPL" in result.query
    mock_client.post.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_uses_cache(settings, cache):
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"results": [], "answer": None}

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    client = TavilyClient(settings=settings, cache=cache, client=mock_client)

    await client.search("same query")
    await client.search("same query")

    mock_client.post.assert_awaited_once()
