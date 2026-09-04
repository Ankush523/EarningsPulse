"""API route tests for playbook and calendar endpoints."""

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.agents.orchestrator import PlaybookOrchestrator
from app.api.deps import get_job_runner
from app.main import app
from app.models.data import EarningsCalendarResponse, EarningsEvent
from app.models.playbook import (
    ConfidenceTier,
    ExecutiveSummary,
    Playbook,
    PlaybookMetadata,
    PlaybookStatus,
    ReactionArchetype,
    ReportForecast,
)
from app.services.job_store import job_store
from app.services.playbook_runner import PlaybookJobRunner
from httpx import ASGITransport, AsyncClient


def _sample_playbook(job_id: str = "job_test") -> Playbook:
    from app.models.playbook import (
        ActionPlaybook,
        ReactionAnalysisSummary,
        SpilloverMap,
    )

    return Playbook(
        metadata=PlaybookMetadata(job_id=job_id),
        executive_summary=ExecutiveSummary(
            ticker="AAPL",
            beat_probability=0.5,
            inline_probability=0.3,
            miss_probability=0.2,
            primary_pattern=ReactionArchetype.DIP_THEN_RALLY,
            primary_pattern_description="Test pattern",
            overall_confidence=ConfidenceTier.MEDIUM,
            top_drivers=["Driver 1"],
        ),
        report_forecast=ReportForecast(
            bull_case="Bull",
            base_case="Base",
            bear_case="Bear",
        ),
        reaction_analysis=ReactionAnalysisSummary(
            archetype=ReactionArchetype.DIP_THEN_RALLY,
            archetype_description="Test",
            confidence=ConfidenceTier.MEDIUM,
        ),
        spillover_map=SpilloverMap(reporting_ticker="AAPL", peers=[]),
        action_playbook=ActionPlaybook(),
    )


@pytest.fixture(autouse=True)
async def clear_job_store():
    await job_store.clear()
    yield
    await job_store.clear()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_runner():
    runner = MagicMock(spec=PlaybookJobRunner)
    runner.start_job = AsyncMock(return_value="job_test123")
    runner.execute_job = AsyncMock()
    return runner


@pytest.fixture
def override_runner(mock_runner):
    app.dependency_overrides[get_job_runner] = lambda: mock_runner
    yield mock_runner
    app.dependency_overrides.pop(get_job_runner, None)


@pytest.mark.asyncio
async def test_generate_playbook(client, override_runner):
    response = await client.post(
        "/api/playbook/generate",
        json={"ticker": "AAPL"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == "job_test123"
    assert data["ticker"] == "AAPL"
    assert data["status"] == "pending"
    assert "/api/playbook/stream/job_test123" in data["stream_url"]
    override_runner.start_job.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_playbook_invalid_ticker(client, override_runner):
    response = await client.post(
        "/api/playbook/generate",
        json={"ticker": "INVALID123"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_playbook_job_not_found(client):
    response = await client.get("/api/playbook/job_does_not_exist")
    assert response.status_code == 404
    assert response.json()["error_code"] == "job_not_found"


@pytest.mark.asyncio
async def test_get_playbook_job_completed(client):
    job = await job_store.create("job_done", "AAPL")
    playbook = _sample_playbook("job_done")
    job.status = PlaybookStatus.COMPLETED
    job.playbook = playbook

    response = await client.get("/api/playbook/job_done")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["playbook"]["executive_summary"]["ticker"] == "AAPL"


@pytest.mark.asyncio
async def test_stream_playbook_events(client):
    job = await job_store.create("job_stream", "NVDA")
    await job_store.append_trace(
        "job_stream",
        {
            "event_id": "evt_1",
            "job_id": "job_stream",
            "event_type": "agent_started",
            "message": "Research started",
            "agent_name": "research",
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )
    job.status = PlaybookStatus.COMPLETED
    job.playbook = _sample_playbook("job_stream")

    response = await client.get("/api/playbook/stream/job_stream")
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    body = response.text
    assert "data:" in body
    assert "agent_start" in body or "research" in body


@pytest.mark.asyncio
async def test_calendar_upcoming(client):
    mock_service = MagicMock()
    mock_service.get_upcoming_earnings = AsyncMock(
        return_value=EarningsCalendarResponse(
            from_date=date(2025, 9, 1),
            to_date=date(2025, 9, 8),
            events=[
                EarningsEvent(ticker="AAPL", report_date=date(2025, 9, 5)),
            ],
        )
    )

    with patch("app.api.routes.calendar.get_earnings_service", return_value=mock_service):
        from app.api.deps import get_earnings_service

        app.dependency_overrides[get_earnings_service] = lambda: mock_service
        try:
            response = await client.get("/api/calendar?days=7")
        finally:
            app.dependency_overrides.pop(get_earnings_service, None)

    assert response.status_code == 200
    data = response.json()
    assert len(data["events"]) == 1
    assert data["events"][0]["ticker"] == "AAPL"


@pytest.mark.asyncio
async def test_calendar_ticker(client):
    mock_service = MagicMock()
    mock_service.get_next_earnings_date = AsyncMock(return_value=date(2025, 9, 10))

    from app.api.deps import get_earnings_service

    app.dependency_overrides[get_earnings_service] = lambda: mock_service
    try:
        response = await client.get("/api/calendar/AAPL")
    finally:
        app.dependency_overrides.pop(get_earnings_service, None)

    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "AAPL"
    assert data["has_upcoming"] is True
    assert data["report_date"] == "2025-09-10"


@pytest.mark.asyncio
async def test_rate_limit_generate(client, override_runner):
    from app.api.rate_limit import playbook_rate_limiter

    original_max = playbook_rate_limiter.max_requests
    playbook_rate_limiter.max_requests = 2
    playbook_rate_limiter._requests.clear()
    try:
        for _ in range(2):
            response = await client.post("/api/playbook/generate", json={"ticker": "AAPL"})
            assert response.status_code == 200

        response = await client.post("/api/playbook/generate", json={"ticker": "MSFT"})
        assert response.status_code == 429
    finally:
        playbook_rate_limiter.max_requests = original_max
        playbook_rate_limiter._requests.clear()


@pytest.mark.asyncio
async def test_execute_job_integration(
    settings,
    mock_research_bundle,
    mock_reaction_analysis,
    mock_peer_map_result,
):
    from app.agents.forecast import ForecastAgent
    from app.agents.mappers import peer_map_to_spillover, reaction_analysis_to_summary
    from app.agents.reaction import ReactionAgent
    from app.agents.research import ResearchAgent
    from app.agents.spillover import SpilloverAgent
    from app.agents.synthesis import SynthesisAgent

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
    runner = PlaybookJobRunner(store=job_store, orchestrator=orchestrator)
    job_id = await runner.start_job("AAPL")
    await runner.execute_job(job_id)

    job = await job_store.get(job_id)
    assert job.status == PlaybookStatus.COMPLETED
    assert job.playbook is not None
    assert job.playbook.executive_summary.ticker == "AAPL"
    assert len(job.trace_events) >= 1
