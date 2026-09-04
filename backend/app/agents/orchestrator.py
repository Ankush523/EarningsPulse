"""LangGraph orchestrator for multi-agent playbook generation."""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any

from langgraph.graph import END, StateGraph

from app.agents.forecast import ForecastAgent
from app.agents.reaction import ReactionAgent
from app.agents.research import ResearchAgent
from app.agents.spillover import SpilloverAgent
from app.agents.synthesis import SynthesisAgent
from app.agents.trace_utils import make_trace_event, trace_to_dict
from app.config import Settings, get_settings
from app.models.agent_state import AgentState, serialize_trace_events
from app.models.playbook import Playbook
from app.models.trace import TraceEventType, TraceLog


class PlaybookOrchestrator:
    """Orchestrate the multi-agent earnings playbook pipeline."""

    def __init__(
        self,
        settings: Settings | None = None,
        research: ResearchAgent | None = None,
        forecast: ForecastAgent | None = None,
        reaction: ReactionAgent | None = None,
        spillover: SpilloverAgent | None = None,
        synthesis: SynthesisAgent | None = None,
    ):
        self._settings = settings or get_settings()
        self._research = research or ResearchAgent(settings=self._settings)
        self._forecast = forecast or ForecastAgent()
        self._reaction = reaction or ReactionAgent()
        self._spillover = spillover or SpilloverAgent()
        self._synthesis = synthesis or SynthesisAgent()
        self._graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(AgentState)

        graph.add_node("gather_parallel", self._parallel_gather_node)
        graph.add_node("run_forecast", self._forecast_node)
        graph.add_node("run_spillover", self._spillover_node)
        graph.add_node("run_synthesis", self._synthesis_node)

        graph.set_entry_point("gather_parallel")
        graph.add_edge("gather_parallel", "run_forecast")
        graph.add_edge("run_forecast", "run_spillover")
        graph.add_edge("run_spillover", "run_synthesis")
        graph.add_edge("run_synthesis", END)

        return graph.compile()

    async def run(
        self,
        ticker: str,
        *,
        job_id: str | None = None,
        earnings_date: str | None = None,
    ) -> Playbook:
        """Run the full agent pipeline and return a complete Playbook."""
        normalized = ticker.upper().strip()
        job_id = job_id or f"job_{uuid.uuid4().hex[:12]}"
        started = time.perf_counter()

        initial_state: AgentState = {
            "job_id": job_id,
            "ticker": normalized,
            "earnings_date": earnings_date,
            "trace_events": [
                trace_to_dict(
                    make_trace_event(
                        job_id,
                        TraceEventType.RUN_STARTED,
                        f"Playbook generation started for {normalized}",
                        input_summary={"ticker": normalized},
                    )
                )
            ],
            "errors": [],
            "messages": [],
            "status": "running",
        }

        final_state = await self._graph.ainvoke(initial_state)

        playbook: Playbook | None = final_state.get("playbook")
        if playbook is None:
            raise RuntimeError("Orchestrator completed without producing a playbook")

        elapsed = int((time.perf_counter() - started) * 1000)
        playbook.metadata.generation_time_ms = elapsed

        final_trace = final_state.get("trace_events", [])
        final_trace.append(
            trace_to_dict(
                make_trace_event(
                    job_id,
                    TraceEventType.RUN_COMPLETED,
                    f"Playbook generation completed for {normalized}",
                    latency_ms=elapsed,
                    output_summary={"ticker": normalized},
                )
            )
        )

        return playbook

    async def run_with_trace(
        self,
        ticker: str,
        *,
        job_id: str | None = None,
        earnings_date: str | None = None,
    ) -> tuple[Playbook, TraceLog]:
        """Run pipeline and return playbook plus full trace log."""
        job_id = job_id or f"job_{uuid.uuid4().hex[:12]}"
        started = time.perf_counter()

        initial_state: AgentState = {
            "job_id": job_id,
            "ticker": ticker.upper().strip(),
            "earnings_date": earnings_date,
            "trace_events": [
                trace_to_dict(
                    make_trace_event(
                        job_id,
                        TraceEventType.RUN_STARTED,
                        f"Playbook generation started for {ticker.upper()}",
                    )
                )
            ],
            "errors": [],
            "messages": [],
            "status": "running",
        }

        final_state = await self._graph.ainvoke(initial_state)
        playbook = final_state.get("playbook")
        if playbook is None:
            raise RuntimeError("Orchestrator completed without producing a playbook")

        elapsed = int((time.perf_counter() - started) * 1000)
        playbook.metadata.generation_time_ms = elapsed

        trace = TraceLog(
            job_id=job_id,
            ticker=ticker.upper(),
            events=serialize_trace_events(final_state.get("trace_events", [])),
            completed_at=playbook.metadata.generated_at,
            total_latency_ms=elapsed,
        )
        return playbook, trace

    async def astream(
        self,
        ticker: str,
        *,
        job_id: str | None = None,
        earnings_date: str | None = None,
    ):
        """
        Stream LangGraph node updates for SSE consumers.

        Yields merged partial state updates including trace_events and playbook.
        """
        normalized = ticker.upper().strip()
        job_id = job_id or f"job_{uuid.uuid4().hex[:12]}"

        initial_state: AgentState = {
            "job_id": job_id,
            "ticker": normalized,
            "earnings_date": earnings_date,
            "trace_events": [
                trace_to_dict(
                    make_trace_event(
                        job_id,
                        TraceEventType.RUN_STARTED,
                        f"Playbook generation started for {normalized}",
                        input_summary={"ticker": normalized},
                    )
                )
            ],
            "errors": [],
            "messages": [],
            "status": "running",
        }

        async for update in self._graph.astream(initial_state, stream_mode="updates"):
            for _node_name, node_output in update.items():
                yield node_output

    async def _parallel_gather_node(self, state: AgentState) -> dict[str, Any]:
        """Run Research and Reaction agents in parallel."""
        research_task = self._research.run(state)
        reaction_task = self._reaction.run(state)
        research_result, reaction_result = await asyncio.gather(research_task, reaction_task)
        return _merge_updates(research_result, reaction_result)

    async def _forecast_node(self, state: AgentState) -> dict[str, Any]:
        return await self._forecast.run(state)

    async def _spillover_node(self, state: AgentState) -> dict[str, Any]:
        return await self._spillover.run(state)

    async def _synthesis_node(self, state: AgentState) -> dict[str, Any]:
        return await self._synthesis.run(state)


def _merge_updates(*updates: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {
        "trace_events": [],
        "errors": [],
    }
    for update in updates:
        for key, value in update.items():
            if key in {"trace_events", "errors"}:
                merged[key].extend(value or [])
            else:
                merged[key] = value
    return merged
