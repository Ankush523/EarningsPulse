"""Integration tests for multi-agent orchestrator."""

from typing import cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.agents.forecast import ForecastAgent
from app.agents.llm import LLMClient
from app.agents.orchestrator import PlaybookOrchestrator
from app.agents.reaction import ReactionAgent
from app.agents.research import ResearchAgent
from app.agents.spillover import SpilloverAgent
from app.agents.synthesis import SynthesisAgent
from app.models.agent_state import AgentState
from app.models.playbook import (
    Playbook,
    ReactionArchetype,
)
from app.services.reaction_analyzer import ReactionAnalyzer


@pytest.mark.asyncio
async def test_orchestrator_returns_complete_playbook(
    settings,
    mock_research_bundle,
    mock_reaction_analysis,
    mock_peer_map_result,
):
    research_agent = ResearchAgent(settings=settings)
    research_agent.run = AsyncMock(
        return_value={"research": mock_research_bundle, "trace_events": [], "errors": []}
    )

    reaction_agent = ReactionAgent()
    reaction_agent.run = AsyncMock(
        return_value={
            "reaction": __import__(
                "app.agents.mappers", fromlist=["reaction_analysis_to_summary"]
            ).reaction_analysis_to_summary(mock_reaction_analysis),
            "trace_events": [],
            "errors": [],
        }
    )

    forecast_agent = ForecastAgent()
    forecast_agent.run = AsyncMock(
        return_value={
            "forecast": {
                "beat_probability": 0.55,
                "inline_probability": 0.28,
                "miss_probability": 0.17,
                "key_metrics": [
                    {
                        "name": "Services revenue",
                        "description": "Key growth driver",
                        "importance": "high",
                    }
                ],
                "bull_case": "Beat on services.",
                "base_case": "Inline report.",
                "bear_case": "Miss on iPhone.",
                "positive_surprises": ["Services beat"],
                "negative_surprises": ["China weakness"],
                "confidence": "medium",
            },
            "trace_events": [],
        }
    )

    spillover_agent = SpilloverAgent()
    spillover_agent.run = AsyncMock(
        return_value={
            "spillover": __import__(
                "app.agents.mappers", fromlist=["peer_map_to_spillover"]
            ).peer_map_to_spillover(mock_peer_map_result),
            "trace_events": [],
            "errors": [],
        }
    )

    orchestrator = PlaybookOrchestrator(
        settings=settings,
        research=research_agent,
        forecast=forecast_agent,
        reaction=reaction_agent,
        spillover=spillover_agent,
        synthesis=SynthesisAgent(),
    )

    playbook = await orchestrator.run("AAPL", job_id="test-job-1")

    assert isinstance(playbook, Playbook)
    assert playbook.executive_summary.ticker == "AAPL"
    assert playbook.executive_summary.beat_probability == 0.55
    assert playbook.reaction_analysis.archetype == ReactionArchetype.DIP_THEN_RALLY
    assert len(playbook.spillover_map.peers) >= 1
    assert len(playbook.action_playbook.rules) >= 1
    assert playbook.metadata.job_id == "test-job-1"
    assert len(playbook.all_sources) >= 1


@pytest.mark.asyncio
async def test_orchestrator_run_with_trace(
    settings, mock_research_bundle, mock_reaction_analysis, mock_peer_map_result
):
    research_agent = ResearchAgent(settings=settings)
    research_agent.run = AsyncMock(
        return_value={"research": mock_research_bundle, "trace_events": [], "errors": []}
    )
    reaction_agent = ReactionAgent()
    reaction_agent.run = AsyncMock(
        return_value={
            "reaction": __import__(
                "app.agents.mappers", fromlist=["reaction_analysis_to_summary"]
            ).reaction_analysis_to_summary(mock_reaction_analysis),
            "trace_events": [],
            "errors": [],
        }
    )
    forecast_agent = ForecastAgent()
    forecast_agent.run = AsyncMock(
        return_value={
            "forecast": {
                "beat_probability": 0.4,
                "inline_probability": 0.35,
                "miss_probability": 0.25,
                "key_metrics": [],
                "bull_case": "Bull",
                "base_case": "Base",
                "bear_case": "Bear",
                "positive_surprises": [],
                "negative_surprises": [],
                "confidence": "low",
            },
            "trace_events": [],
        }
    )
    spillover_agent = SpilloverAgent()
    spillover_agent.run = AsyncMock(
        return_value={
            "spillover": __import__(
                "app.agents.mappers", fromlist=["peer_map_to_spillover"]
            ).peer_map_to_spillover(mock_peer_map_result),
            "trace_events": [],
            "errors": [],
        }
    )

    orchestrator = PlaybookOrchestrator(
        research=research_agent,
        forecast=forecast_agent,
        reaction=reaction_agent,
        spillover=spillover_agent,
    )

    playbook, trace = await orchestrator.run_with_trace("AAPL")
    assert playbook.executive_summary.ticker == "AAPL"
    assert len(trace.events) >= 1


@pytest.mark.asyncio
async def test_research_agent_fallback_without_keys(cache, settings):
    settings_no_keys = settings.model_copy(update={"tavily_api_key": None, "finnhub_api_key": None})
    agent = ResearchAgent(settings=settings_no_keys)
    agent._price_data.get_company_name = MagicMock(return_value="Apple Inc.")
    agent._earnings.get_next_earnings_date = AsyncMock(return_value=None)

    state = cast(
        AgentState, {"job_id": "job-r1", "ticker": "AAPL", "trace_events": [], "errors": []}
    )
    result = await agent.run(state)

    assert result["research"]["ticker"] == "AAPL"
    assert result["research"]["recent_news"]


@pytest.mark.asyncio
async def test_forecast_agent_heuristic_fallback(settings):
    settings_no_llm = settings.model_copy(update={"openai_api_key": None})
    agent = ForecastAgent(llm=LLMClient(settings=settings_no_llm))
    state = cast(
        AgentState,
        {
            "job_id": "job-f1",
            "ticker": "AAPL",
            "research": {
                "ticker": "AAPL",
                "recent_news": [{"title": "Apple beat estimates", "content": "strong growth"}],
                "analyst_context": "beat expected",
                "sector_context": "",
            },
        },
    )
    result = await agent.run(state)
    forecast = result["forecast"]
    total = (
        forecast["beat_probability"] + forecast["inline_probability"] + forecast["miss_probability"]
    )
    assert abs(total - 1.0) < 0.01
    assert forecast["bull_case"]


@pytest.mark.asyncio
async def test_reaction_agent_with_mock_analyzer(mock_reaction_analysis):
    analyzer = ReactionAnalyzer()
    analyzer.analyze_ticker = AsyncMock(return_value=mock_reaction_analysis)

    agent = ReactionAgent(analyzer=analyzer)
    result = await agent.run(cast(AgentState, {"job_id": "job-react", "ticker": "AAPL"}))

    assert result["reaction"].archetype == ReactionArchetype.DIP_THEN_RALLY


@pytest.mark.asyncio
async def test_spillover_agent_with_mock_peer_map(cache, mock_peer_map_result):
    from app.agents.spillover import SpilloverAgent
    from app.services.peer_map import PeerMapService

    service = PeerMapService(cache=cache)
    service.build_peer_map = AsyncMock(return_value=mock_peer_map_result)

    agent = SpilloverAgent(peer_map=service)

    state = cast(
        AgentState,
        {
            "job_id": "job-spill",
            "ticker": "AAPL",
            "research": {
                "ticker": "AAPL",
                "sector": "Technology",
                "industry": "Consumer Electronics",
            },
        },
    )
    result = await agent.run(state)

    spillover = result["spillover"]
    assert spillover.reporting_ticker == "AAPL"
    assert len(spillover.peers) >= 1
    assert result["trace_events"]


@pytest.mark.asyncio
async def test_synthesis_agent_builds_playbook(
    mock_research_bundle,
    mock_reaction_analysis,
    mock_peer_map_result,
):
    from app.agents.mappers import (
        peer_map_to_spillover,
        reaction_analysis_to_summary,
    )
    from app.agents.synthesis import SynthesisAgent

    agent = SynthesisAgent()
    state = cast(
        AgentState,
        {
            "job_id": "job-synth",
            "ticker": "AAPL",
            "research": mock_research_bundle,
            "forecast": {
                "beat_probability": 0.5,
                "inline_probability": 0.3,
                "miss_probability": 0.2,
                "key_metrics": [
                    {
                        "name": "Services",
                        "description": "Growth driver",
                        "importance": "high",
                    }
                ],
                "bull_case": "Beat case",
                "base_case": "Base case",
                "bear_case": "Bear case",
                "positive_surprises": ["Services beat"],
                "negative_surprises": [],
                "confidence": "medium",
            },
            "reaction": reaction_analysis_to_summary(mock_reaction_analysis),
            "spillover": peer_map_to_spillover(mock_peer_map_result),
        },
    )

    result = await agent.run(state)
    playbook = result["playbook"]

    assert playbook.executive_summary.ticker == "AAPL"
    assert playbook.report_forecast.bull_case == "Beat case"
    assert len(playbook.action_playbook.rules) >= 1
    assert playbook.metadata.job_id == "job-synth"


@pytest.mark.asyncio
async def test_orchestrator_astream_yields_updates(
    settings,
    mock_research_bundle,
    mock_reaction_analysis,
    mock_peer_map_result,
):
    from app.agents.mappers import peer_map_to_spillover, reaction_analysis_to_summary

    research_agent = ResearchAgent(settings=settings)
    research_agent.run = AsyncMock(
        return_value={"research": mock_research_bundle, "trace_events": [], "errors": []}
    )
    reaction_agent = ReactionAgent()
    reaction_agent.run = AsyncMock(
        return_value={
            "reaction": reaction_analysis_to_summary(mock_reaction_analysis),
            "trace_events": [],
            "errors": [],
        }
    )
    forecast_agent = ForecastAgent()
    forecast_agent.run = AsyncMock(
        return_value={
            "forecast": {
                "beat_probability": 0.5,
                "inline_probability": 0.3,
                "miss_probability": 0.2,
                "key_metrics": [],
                "bull_case": "Bull",
                "base_case": "Base",
                "bear_case": "Bear",
                "positive_surprises": [],
                "negative_surprises": [],
                "confidence": "medium",
            },
            "trace_events": [],
        }
    )
    spillover_agent = SpilloverAgent()
    spillover_agent.run = AsyncMock(
        return_value={
            "spillover": peer_map_to_spillover(mock_peer_map_result),
            "trace_events": [],
            "errors": [],
        }
    )

    orchestrator = PlaybookOrchestrator(
        settings=settings,
        research=research_agent,
        forecast=forecast_agent,
        reaction=reaction_agent,
        spillover=spillover_agent,
        synthesis=SynthesisAgent(),
    )

    updates = []
    async for update in orchestrator.astream("AAPL", job_id="job-stream-test"):
        updates.append(update)

    assert len(updates) >= 3
    assert any(u.get("playbook") is not None for u in updates)
