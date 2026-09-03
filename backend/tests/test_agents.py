"""Integration tests for multi-agent orchestrator."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.forecast import ForecastAgent
from app.agents.llm import LLMClient
from app.agents.orchestrator import PlaybookOrchestrator
from app.agents.reaction import ReactionAgent
from app.agents.research import ResearchAgent
from app.agents.spillover import SpilloverAgent
from app.agents.synthesis import SynthesisAgent
from app.models.analysis import PeerMapResult, ReactionPatternAnalysis
from app.models.data import EarningsEvent, HistoricalEarningsResponse, OHLCVBar
from app.models.playbook import (
    ConfidenceTier,
    Playbook,
    ReactionArchetype,
    ReportOutcome,
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
async def test_orchestrator_run_with_trace(settings, mock_research_bundle, mock_reaction_analysis, mock_peer_map_result):
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
    settings_no_keys = settings.model_copy(
        update={"tavily_api_key": None, "finnhub_api_key": None}
    )
    agent = ResearchAgent(settings=settings_no_keys)
    agent._price_data.get_company_name = MagicMock(return_value="Apple Inc.")
    agent._earnings.get_next_earnings_date = AsyncMock(return_value=None)

    state = {"job_id": "job-r1", "ticker": "AAPL", "trace_events": [], "errors": []}
    result = await agent.run(state)

    assert result["research"]["ticker"] == "AAPL"
    assert result["research"]["recent_news"]


@pytest.mark.asyncio
async def test_forecast_agent_heuristic_fallback(settings):
    settings_no_llm = settings.model_copy(update={"openai_api_key": None})
    agent = ForecastAgent(llm=LLMClient(settings=settings_no_llm))
    state = {
        "job_id": "job-f1",
        "ticker": "AAPL",
        "research": {
            "ticker": "AAPL",
            "recent_news": [{"title": "Apple beat estimates", "content": "strong growth"}],
            "analyst_context": "beat expected",
            "sector_context": "",
        },
    }
    result = await agent.run(state)
    forecast = result["forecast"]
    total = forecast["beat_probability"] + forecast["inline_probability"] + forecast["miss_probability"]
    assert abs(total - 1.0) < 0.01
    assert forecast["bull_case"]


@pytest.mark.asyncio
async def test_reaction_agent_with_mock_analyzer(mock_reaction_analysis):
    analyzer = ReactionAnalyzer()
    analyzer.analyze_ticker = AsyncMock(return_value=mock_reaction_analysis)

    agent = ReactionAgent(analyzer=analyzer)
    result = await agent.run({"job_id": "job-react", "ticker": "AAPL"})

    assert result["reaction"].archetype == ReactionArchetype.DIP_THEN_RALLY
