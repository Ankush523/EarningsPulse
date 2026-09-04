"""Reaction agent — historical earnings pattern analysis."""

from __future__ import annotations

import time
from typing import Any

from app.agents.mappers import reaction_analysis_to_summary
from app.agents.trace_utils import make_trace_event, trace_to_dict, traced_tool
from app.config import get_settings
from app.models.agent_state import AgentState
from app.models.playbook import ConfidenceTier, ReactionAnalysisSummary, ReactionArchetype
from app.models.trace import TraceEventType
from app.services.reaction_analyzer import ReactionAnalyzer

AGENT_NAME = "reaction"


class ReactionAgent:
    """Analyze historical earnings price reactions."""

    def __init__(self, analyzer: ReactionAnalyzer | None = None):
        self._analyzer = analyzer or ReactionAnalyzer()

    async def run(self, state: AgentState) -> dict[str, Any]:
        job_id = state["job_id"]
        ticker = state["ticker"].upper()
        started = time.perf_counter()
        trace_events: list[dict[str, Any]] = [
            trace_to_dict(
                make_trace_event(
                    job_id,
                    TraceEventType.AGENT_STARTED,
                    f"Reaction agent started for {ticker}",
                    agent_name=AGENT_NAME,
                )
            )
        ]
        errors: list[str] = []

        settings = get_settings()
        try:
            async with traced_tool(
                job_id,
                AGENT_NAME,
                "reaction_analyzer",
                {
                    "ticker": ticker,
                    "limit": settings.reaction_history_limit,
                    "backtest_years_target": 10,
                },
            ) as tool_events:
                analysis = await self._analyzer.analyze_ticker(
                    ticker,
                    limit=settings.reaction_history_limit,
                )
                trace_events.extend(trace_to_dict(e) for e in tool_events)
            reaction: ReactionAnalysisSummary = reaction_analysis_to_summary(analysis)
        except Exception as exc:
            errors.append(f"reaction_analyzer: {exc}")
            reaction = ReactionAnalysisSummary(
                archetype=ReactionArchetype.INSUFFICIENT_DATA,
                archetype_description="Insufficient historical data for pattern analysis.",
                confidence=ConfidenceTier.LOW,
            )

        trace_events.append(
            trace_to_dict(
                make_trace_event(
                    job_id,
                    TraceEventType.AGENT_COMPLETED,
                    f"Reaction agent completed for {ticker}",
                    agent_name=AGENT_NAME,
                    output_summary={"archetype": reaction.archetype.value},
                    latency_ms=int((time.perf_counter() - started) * 1000),
                )
            )
        )

        return {
            "reaction": reaction,
            "trace_events": trace_events,
            "errors": errors,
            "current_agent": AGENT_NAME,
        }
