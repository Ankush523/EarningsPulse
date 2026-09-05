"""Tests for PRISM client, trace store, and trace API."""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.agents.trace_utils import make_trace_event, trace_to_dict
from app.api.deps import get_trace_store
from app.config import Settings
from app.main import app
from app.models.trace import TraceEventType, TraceLog
from app.services.job_store import job_store
from app.services.prism_client import PrismClient
from app.services.trace_store import TraceStore, trace_event_to_prism_step
from httpx import ASGITransport, AsyncClient


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
def trace_settings(tmp_path: Path) -> Settings:
    return Settings(
        finnhub_api_key="test-finnhub-key",
        tavily_api_key="test-tavily-key",
        sec_user_agent="EarningsPulse test@example.com",
        trace_log_dir=str(tmp_path / "traces"),
    )


def test_trace_event_to_prism_step_maps_tool_call():
    event = make_trace_event(
        "job_1",
        TraceEventType.TOOL_CALL_COMPLETED,
        "tavily_search completed",
        agent_name="research",
        tool_name="tavily_search",
        latency_ms=120,
    )
    step = trace_event_to_prism_step(event)
    assert step["step_type"] == "tool_call"
    assert step["tool_name"] == "tavily_search"
    assert step["duration_ms"] == 120


@pytest.mark.asyncio
async def test_build_trace_log_from_job(trace_settings):
    store = TraceStore(store=job_store, settings=trace_settings)

    job = await job_store.create("job_trace1", "AAPL")
    await job_store.append_trace(
        "job_trace1",
        trace_to_dict(
            make_trace_event(
                "job_trace1",
                TraceEventType.RUN_STARTED,
                "Started",
                input_summary={"ticker": "AAPL"},
            )
        ),
    )
    await job_store.append_trace(
        "job_trace1",
        trace_to_dict(
            make_trace_event(
                "job_trace1",
                TraceEventType.RUN_COMPLETED,
                "Completed",
                latency_ms=1500,
            )
        ),
    )
    job.completed_at = datetime.now(UTC)
    trace_log = store.build_trace_log(job)
    assert trace_log.job_id == "job_trace1"
    assert trace_log.ticker == "AAPL"
    assert len(trace_log.events) == 2
    assert trace_log.total_latency_ms == 1500
    assert trace_log.prism_synced is False


@pytest.mark.asyncio
async def test_save_and_load_trace_log(trace_settings):
    store = TraceStore(store=job_store, settings=trace_settings)
    trace_log = TraceLog(
        job_id="job_persist",
        ticker="NVDA",
        events=[
            make_trace_event(
                "job_persist",
                TraceEventType.RUN_STARTED,
                "Started",
            )
        ],
    )
    path = await store.save_trace_log(trace_log)
    assert path.exists()

    loaded = store._load_from_disk("job_persist")
    assert loaded is not None
    assert loaded.job_id == "job_persist"
    assert len(loaded.events) == 1


@pytest.mark.asyncio
async def test_get_trace_api_not_found(client, trace_settings):
    app.dependency_overrides[get_trace_store] = lambda: TraceStore(
        store=job_store, settings=trace_settings
    )
    try:
        response = await client.get("/api/trace/job_missing")
    finally:
        app.dependency_overrides.pop(get_trace_store, None)

    assert response.status_code == 404
    assert response.json()["error_code"] == "job_not_found"


@pytest.mark.asyncio
async def test_get_trace_api_completed_job(client, trace_settings):
    job = await job_store.create("job_api_trace", "MSFT")
    await job_store.append_trace(
        "job_api_trace",
        trace_to_dict(
            make_trace_event(
                "job_api_trace",
                TraceEventType.AGENT_STARTED,
                "Research agent started",
                agent_name="research",
            )
        ),
    )
    job.completed_at = datetime.now(UTC)

    app.dependency_overrides[get_trace_store] = lambda: TraceStore(
        store=job_store, settings=trace_settings
    )
    try:
        response = await client.get("/api/trace/job_api_trace")
    finally:
        app.dependency_overrides.pop(get_trace_store, None)

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == "job_api_trace"
    assert data["ticker"] == "MSFT"
    assert len(data["events"]) == 1
    assert data["events"][0]["event_type"] == "agent_started"


@pytest.mark.asyncio
async def test_prism_client_local_mode_does_not_sync(trace_settings):
    settings = trace_settings.model_copy(
        update={"prism_api_key": None, "prism_project_id": None},
    )
    client = PrismClient(settings=settings)
    assert client.local_mode is True

    trace_log = TraceLog(
        job_id="job_local",
        ticker="AAPL",
        events=[make_trace_event("job_local", TraceEventType.RUN_STARTED, "Started")],
    )
    synced = await client.sync_trace_log(trace_log)
    assert synced is False


@pytest.mark.asyncio
async def test_prism_client_sync_with_rest_fallback(trace_settings):
    settings = trace_settings.model_copy(
        update={
            "prism_api_key": "pt-sk-test-key",
            "prism_project_id": "proj_test",
        }
    )
    client = PrismClient(settings=settings)
    client._sdk = None  # force REST path for this test
    assert client.local_mode is False

    trace_log = TraceLog(
        job_id="job_remote",
        ticker="AAPL",
        events=[
            make_trace_event(
                "job_remote",
                TraceEventType.AGENT_STARTED,
                "Research started",
                agent_name="research",
            ),
            make_trace_event(
                "job_remote",
                TraceEventType.RUN_COMPLETED,
                "Done",
                latency_ms=900,
            ),
        ],
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "ok"

    mock_http = AsyncMock()
    mock_http.post = AsyncMock(return_value=mock_response)
    mock_http.is_closed = False

    with patch.object(client, "_get_http_client", AsyncMock(return_value=mock_http)):
        synced = await client.sync_trace_log(trace_log)

    assert synced is True
    assert mock_http.post.await_count == 2
    trajectory_call = mock_http.post.await_args_list[0]
    trace_call = mock_http.post.await_args_list[1]
    assert "trajectories" in trajectory_call.args[0]
    assert "traces" in trace_call.args[0]
    assert trajectory_call.kwargs["json"]["project_id"] == "proj_test"
    assert len(trajectory_call.kwargs["json"]["steps"]) == 2


@pytest.mark.asyncio
async def test_prism_emit_buffers_when_enabled(trace_settings):
    settings = trace_settings.model_copy(
        update={
            "prism_api_key": "pt-sk-test-key",
            "prism_project_id": "proj_test",
        }
    )
    client = PrismClient(settings=settings)
    event = make_trace_event(
        "job_buf",
        TraceEventType.TOOL_CALL_STARTED,
        "tool start",
        tool_name="yfinance",
    )
    await client.emit(event)
    assert "job_buf" in client._buffers
    assert len(client._buffers["job_buf"]) == 1
