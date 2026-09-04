"""Research agent — gathers context from Tavily, EDGAR, and earnings calendar."""

from __future__ import annotations

import time
from typing import Any

from app.agents.trace_utils import make_trace_event, trace_to_dict, traced_tool
from app.config import Settings, get_settings
from app.models.agent_state import AgentState, ResearchBundle
from app.models.trace import TraceEventType
from app.services.earnings_calendar import EarningsCalendarService
from app.services.edgar_client import EdgarClient
from app.services.errors import ConfigurationError, ServiceError
from app.services.price_data import PriceDataService
from app.services.tavily_client import TavilyClient

AGENT_NAME = "research"


class ResearchAgent:
    """Collect pre-earnings research from external data sources."""

    def __init__(
        self,
        settings: Settings | None = None,
        tavily: TavilyClient | None = None,
        edgar: EdgarClient | None = None,
        earnings: EarningsCalendarService | None = None,
        price_data: PriceDataService | None = None,
    ):
        self._settings = settings or get_settings()
        self._tavily = tavily or TavilyClient(settings=self._settings)
        self._edgar = edgar or EdgarClient(settings=self._settings)
        self._earnings = earnings or EarningsCalendarService(settings=self._settings)
        self._price_data = price_data or PriceDataService()

    async def run(self, state: AgentState) -> dict[str, Any]:
        job_id = state["job_id"]
        ticker = state["ticker"].upper()
        started = time.perf_counter()
        trace_events: list[dict[str, Any]] = [
            trace_to_dict(
                make_trace_event(
                    job_id,
                    TraceEventType.AGENT_STARTED,
                    f"Research agent started for {ticker}",
                    agent_name=AGENT_NAME,
                )
            )
        ]
        errors: list[str] = []

        company_name = self._price_data.get_company_name(ticker)
        earnings_date = state.get("earnings_date")
        is_after_hours = True

        try:
            if not earnings_date:
                next_date = await self._earnings.get_next_earnings_date(ticker)
                earnings_date = next_date.isoformat() if next_date else None
        except Exception as exc:
            errors.append(f"earnings_date: {exc}")

        sources: list[dict[str, Any]] = []
        recent_news: list[dict[str, Any]] = []
        filing_links: list[dict[str, str]] = []
        analyst_context = ""
        sector_context = ""
        last_earnings_summary = ""
        sector: str | None = None
        industry: str | None = None

        # Tavily — company news
        try:
            async with traced_tool(
                job_id, AGENT_NAME, "tavily_company_news", {"ticker": ticker}
            ) as tool_events:
                news = await self._tavily.search_company_news(ticker, company_name, days=90)
                trace_events.extend(trace_to_dict(e) for e in tool_events)
            recent_news = [
                {
                    "title": r.title,
                    "url": r.url,
                    "content": r.content[:500],
                    "score": r.score,
                }
                for r in news.results
            ]
            if news.answer:
                analyst_context = news.answer
            for r in news.results[:5]:
                sources.append({"title": r.title, "url": r.url, "source_type": "tavily"})
        except (ConfigurationError, ServiceError) as exc:
            errors.append(f"tavily_news: {exc}")
            recent_news = _fallback_news(ticker, company_name)

        # Tavily — earnings preview
        try:
            async with traced_tool(
                job_id, AGENT_NAME, "tavily_earnings_preview", {"ticker": ticker}
            ) as tool_events:
                preview = await self._tavily.search_earnings_preview(ticker, company_name)
                trace_events.extend(trace_to_dict(e) for e in tool_events)
            if preview.answer:
                analyst_context = (
                    f"{analyst_context}\n\n{preview.answer}".strip()
                    if analyst_context
                    else preview.answer
                )
            for r in preview.results[:3]:
                sources.append({"title": r.title, "url": r.url, "source_type": "tavily"})
        except (ConfigurationError, ServiceError) as exc:
            errors.append(f"tavily_preview: {exc}")

        # EDGAR filings
        try:
            async with traced_tool(
                job_id, AGENT_NAME, "edgar_filings", {"ticker": ticker}
            ) as tool_events:
                filings = await self._edgar.get_filings(ticker)
                trace_events.extend(trace_to_dict(e) for e in tool_events)
            sector = filings.company_name
            if filings.latest_quarterly:
                filing_links.append(
                    {
                        "form": filings.latest_quarterly.form_type.value,
                        "url": filings.latest_quarterly.document_url,
                        "date": filings.latest_quarterly.filing_date.isoformat(),
                    }
                )
                last_earnings_summary = (
                    f"Latest {filings.latest_quarterly.form_type.value} filed "
                    f"{filings.latest_quarterly.filing_date.isoformat()}"
                )
                sources.append(
                    {
                        "title": filings.latest_quarterly.form_type.value,
                        "url": filings.latest_quarterly.document_url,
                        "source_type": "edgar",
                    }
                )
            if filings.latest_annual:
                filing_links.append(
                    {
                        "form": filings.latest_annual.form_type.value,
                        "url": filings.latest_annual.document_url,
                        "date": filings.latest_annual.filing_date.isoformat(),
                    }
                )
        except (ConfigurationError, ServiceError) as exc:
            errors.append(f"edgar: {exc}")
            last_earnings_summary = last_earnings_summary or f"No EDGAR data for {ticker}"

        # Sector context
        try:
            async with traced_tool(
                job_id,
                AGENT_NAME,
                "tavily_sector_context",
                {"ticker": ticker},
            ) as tool_events:
                sector_search = await self._tavily.search_sector_context(ticker)
                trace_events.extend(trace_to_dict(e) for e in tool_events)
            sector_context = sector_search.answer or ""
            for r in sector_search.results[:2]:
                sources.append({"title": r.title, "url": r.url, "source_type": "tavily"})
        except (ConfigurationError, ServiceError) as exc:
            errors.append(f"tavily_sector: {exc}")

        research: ResearchBundle = {
            "ticker": ticker,
            "company_name": company_name,
            "earnings_date": earnings_date,
            "is_after_hours": is_after_hours,
            "last_earnings_summary": last_earnings_summary or f"Research gathered for {ticker}",
            "recent_news": recent_news,
            "filing_links": filing_links,
            "analyst_context": analyst_context or "No analyst context available.",
            "sector_context": sector_context or "No sector context available.",
            "sector": sector,
            "industry": industry,
            "sources": sources,
        }

        trace_events.append(
            trace_to_dict(
                make_trace_event(
                    job_id,
                    TraceEventType.AGENT_COMPLETED,
                    f"Research agent completed for {ticker}",
                    agent_name=AGENT_NAME,
                    output_summary={
                        "news_count": len(recent_news),
                        "filings_count": len(filing_links),
                        "sources_count": len(sources),
                    },
                    latency_ms=int((time.perf_counter() - started) * 1000),
                )
            )
        )

        return {
            "research": research,
            "trace_events": trace_events,
            "errors": errors,
            "current_agent": AGENT_NAME,
        }


def _fallback_news(ticker: str, company_name: str | None) -> list[dict[str, Any]]:
    name = company_name or ticker
    return [
        {
            "title": f"{name} pre-earnings context",
            "url": f"https://finance.yahoo.com/quote/{ticker}",
            "content": (
                f"Monitor {name} ahead of upcoming earnings "
                "for estimate revisions and sector trends."
            ),
            "score": None,
        }
    ]
