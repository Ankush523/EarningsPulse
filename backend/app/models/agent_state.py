"""LangGraph agent state schema."""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from app.models.playbook import Playbook, ReactionAnalysisSummary, SpilloverMap
from app.models.trace import TraceEvent


class ResearchBundle(TypedDict, total=False):
    """Output from the Research Agent."""

    ticker: str
    company_name: str | None
    earnings_date: str | None
    is_after_hours: bool
    last_earnings_summary: str
    recent_news: list[dict[str, Any]]
    filing_links: list[dict[str, str]]
    analyst_context: str
    sector_context: str
    sector: str | None
    industry: str | None
    sources: list[dict[str, Any]]


class ForecastResult(TypedDict, total=False):
    """Output from the Forecast Agent."""

    beat_probability: float
    inline_probability: float
    miss_probability: float
    key_metrics: list[dict[str, Any]]
    bull_case: str
    base_case: str
    bear_case: str
    positive_surprises: list[str]
    negative_surprises: list[str]
    confidence: str


class AgentState(TypedDict, total=False):
    """Shared state passed through the LangGraph orchestrator."""

    # Input
    job_id: str
    ticker: str
    earnings_date: str | None

    # Agent outputs
    research: ResearchBundle | None
    forecast: ForecastResult | None
    reaction: ReactionAnalysisSummary | None
    spillover: SpilloverMap | None
    playbook: Playbook | None

    # Observability — reducers merge lists across parallel nodes
    trace_events: Annotated[list[dict[str, Any]], operator.add]
    errors: Annotated[list[str], operator.add]

    # LangGraph message history (optional, for future LLM tool loops)
    messages: Annotated[list[Any], operator.add]

    # Control flow
    current_agent: str | None
    status: str


def serialize_trace_events(events: list[dict[str, Any]] | list[TraceEvent]) -> list[TraceEvent]:
    """Convert trace dicts back to TraceEvent models."""
    parsed: list[TraceEvent] = []
    for item in events:
        if isinstance(item, TraceEvent):
            parsed.append(item)
        else:
            parsed.append(TraceEvent.model_validate(item))
    return parsed
