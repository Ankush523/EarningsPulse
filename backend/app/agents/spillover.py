"""Spillover agent — peer map and sympathy move analysis."""

from __future__ import annotations

import time
from typing import Any

from app.agents.mappers import peer_map_to_spillover
from app.agents.trace_utils import make_trace_event, trace_to_dict, traced_tool
from app.models.agent_state import AgentState, ResearchBundle
from app.models.playbook import ConfidenceTier, SpilloverMap
from app.models.trace import TraceEventType
from app.services.peer_map import PeerMapService
from app.services.tavily_client import TavilyClient

AGENT_NAME = "spillover"


class SpilloverAgent:
    """Map peer spillover for the reporting ticker."""

    def __init__(
        self,
        peer_map: PeerMapService | None = None,
        tavily: TavilyClient | None = None,
    ):
        self._peer_map = peer_map or PeerMapService()
        self._tavily = tavily or TavilyClient()

    async def run(self, state: AgentState) -> dict[str, Any]:
        job_id = state["job_id"]
        ticker = state["ticker"].upper()
        research: ResearchBundle = state.get("research") or {}
        started = time.perf_counter()

        trace_events: list[dict[str, Any]] = [
            trace_to_dict(
                make_trace_event(
                    job_id,
                    TraceEventType.AGENT_STARTED,
                    f"Spillover agent started for {ticker}",
                    agent_name=AGENT_NAME,
                )
            )
        ]
        errors: list[str] = []

        try:
            async with traced_tool(
                job_id, AGENT_NAME, "peer_map", {"ticker": ticker}
            ) as tool_events:
                peer_result = await self._peer_map.build_peer_map(ticker, max_peers=10)
                trace_events.extend(trace_to_dict(e) for e in tool_events)
            spillover: SpilloverMap = peer_map_to_spillover(peer_result)

            # Enrich with sector context if Tavily available
            sector = research.get("sector") or peer_result.sector
            if sector:
                try:
                    async with traced_tool(
                        job_id,
                        AGENT_NAME,
                        "tavily_peer_context",
                        {"ticker": ticker, "sector": sector},
                    ) as tool_events:
                        await self._tavily.search_sector_context(ticker, sector)
                        trace_events.extend(trace_to_dict(e) for e in tool_events)
                except Exception as exc:
                    errors.append(f"tavily_peer_context: {exc}")

        except Exception as exc:
            errors.append(f"peer_map: {exc}")
            spillover = SpilloverMap(
                reporting_ticker=ticker,
                peers=[],
                confidence=ConfidenceTier.LOW,
            )

        trace_events.append(
            trace_to_dict(
                make_trace_event(
                    job_id,
                    TraceEventType.AGENT_COMPLETED,
                    f"Spillover agent completed for {ticker}",
                    agent_name=AGENT_NAME,
                    output_summary={"peer_count": len(spillover.peers)},
                    latency_ms=int((time.perf_counter() - started) * 1000),
                )
            )
        )

        return {
            "spillover": spillover,
            "trace_events": trace_events,
            "errors": errors,
            "current_agent": AGENT_NAME,
        }
