"""LangGraph agent state schema."""

from typing import Any, TypedDict

from app.models.playbook import (
    Playbook,
    ReactionAnalysisSummary,
    SpilloverMap,
)
from app.models.trace import TraceEvent


class ResearchBundle(TypedDict, total=False):
    """Output from the Research Agent."""

    ticker: str
    company_name: str | None
    earnings_date: str | None
    last_earnings_summary: str
    recent_news: list[dict[str, Any]]
    filing_links: list[dict[str, str]]
    analyst_context: str
    sector_context: str
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

    # Observability
    trace_events: list[TraceEvent]
    errors: list[str]

    # LangGraph message history (for LLM agents) — Annotated reducer added in Phase 3
    messages: list[Any]

    # Control flow
    current_agent: str | None
    status: str
