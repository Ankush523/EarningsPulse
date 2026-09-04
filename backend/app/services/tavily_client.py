"""Tavily API wrapper for live web research."""

from __future__ import annotations

import httpx

from app.config import Settings, get_settings
from app.models.data import TavilySearchResponse, TavilySearchResult
from app.services.errors import ConfigurationError, ServiceError
from app.utils.cache import TTLCache, app_cache

TAVILY_SEARCH_URL = "https://api.tavily.com/search"


class TavilyClient:
    """Search the live web via Tavily."""

    def __init__(
        self,
        settings: Settings | None = None,
        cache: TTLCache | None = None,
        client: httpx.AsyncClient | None = None,
    ):
        self._settings = settings or get_settings()
        self._cache = cache or app_cache
        self._client = client

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is not None:
            return self._client
        return httpx.AsyncClient(timeout=45.0)

    def _require_api_key(self) -> str:
        if not self._settings.tavily_api_key:
            raise ConfigurationError(
                "TAVILY_API_KEY is not configured",
                service="tavily",
            )
        return self._settings.tavily_api_key

    async def search(
        self,
        query: str,
        *,
        max_results: int = 5,
        search_depth: str = "basic",
        days: int | None = None,
        include_answer: bool = True,
        use_cache: bool = True,
    ) -> TavilySearchResponse:
        """Run a Tavily web search."""
        cache_key = TTLCache.make_key(
            "tavily_search",
            query,
            max_results,
            search_depth,
            days,
            include_answer,
        )
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        api_key = self._require_api_key()
        payload: dict = {
            "api_key": api_key,
            "query": query,
            "search_depth": search_depth,
            "max_results": max_results,
            "include_answer": include_answer,
        }
        if days is not None:
            payload["days"] = days

        owns_client = self._client is None
        client = await self._get_client()

        try:
            response = await client.post(TAVILY_SEARCH_URL, json=payload)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            raise ServiceError(
                f"Tavily search failed: {exc.response.text}",
                service="tavily",
                retryable=exc.response.status_code >= 500,
            ) from exc
        except httpx.HTTPError as exc:
            raise ServiceError(
                f"Tavily search failed: {exc}",
                service="tavily",
                retryable=True,
            ) from exc
        finally:
            if owns_client:
                await client.aclose()

        results = [
            TavilySearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                content=item.get("content", ""),
                score=item.get("score"),
                published_date=item.get("published_date"),
            )
            for item in data.get("results", [])
        ]

        parsed = TavilySearchResponse(
            query=query,
            results=results,
            answer=data.get("answer"),
            response_time=data.get("response_time"),
        )

        if use_cache:
            self._cache.set(cache_key, parsed, ttl_seconds=900)

        return parsed

    async def search_company_news(
        self,
        ticker: str,
        company_name: str | None = None,
        *,
        days: int = 90,
        max_results: int = 8,
    ) -> TavilySearchResponse:
        """Search recent news for a company."""
        name_part = company_name or ticker
        query = f"{name_part} ({ticker}) stock news last {days} days"
        return await self.search(
            query,
            max_results=max_results,
            days=days,
            include_answer=True,
        )

    async def search_earnings_preview(
        self,
        ticker: str,
        company_name: str | None = None,
    ) -> TavilySearchResponse:
        """Search earnings preview and analyst context."""
        name_part = company_name or ticker
        query = f"{name_part} ({ticker}) earnings preview analyst estimates revenue EPS guidance"
        return await self.search(
            query,
            max_results=8,
            days=90,
            include_answer=True,
        )

    async def search_sector_context(
        self,
        ticker: str,
        sector: str | None = None,
    ) -> TavilySearchResponse:
        """Search sector and thematic context for spillover research."""
        sector_part = sector or "sector"
        query = f"{ticker} {sector_part} industry peers market outlook"
        return await self.search(
            query,
            max_results=6,
            days=60,
            include_answer=True,
        )
