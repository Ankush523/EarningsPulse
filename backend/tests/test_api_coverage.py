"""Additional API endpoint coverage tests."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.main import app
from app.models.playbook import PlaybookStatus
from app.services.job_store import job_store
from httpx import ASGITransport, AsyncClient
from tests.test_api_playbook import _sample_playbook


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


@pytest.mark.asyncio
async def test_readiness_includes_service_checks(client):
    response = await client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "checks" in data
    assert data["checks"]["api"] is True


@pytest.mark.asyncio
async def test_calendar_ticker_endpoint(client):
    mock_service = MagicMock()
    mock_service.get_next_earnings_date = AsyncMock(
        return_value=__import__("datetime").date(2025, 9, 10)
    )

    from app.api.deps import get_earnings_service

    app.dependency_overrides[get_earnings_service] = lambda: mock_service
    try:
        response = await client.get("/api/calendar/AAPL")
    finally:
        app.dependency_overrides.pop(get_earnings_service, None)

    assert response.status_code == 200
    assert response.json()["ticker"] == "AAPL"
    assert response.json()["has_upcoming"] is True


@pytest.mark.asyncio
async def test_openapi_docs_available(client):
    response = await client.get("/docs")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_sse_stream_includes_data_prefix(client):
    job = await job_store.create("job_sse_fmt", "AAPL")
    await job_store.append_trace(
        "job_sse_fmt",
        {
            "event_id": "evt_sse",
            "job_id": "job_sse_fmt",
            "event_type": "run_started",
            "message": "Started",
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )
    job.status = PlaybookStatus.COMPLETED
    job.playbook = _sample_playbook("job_sse_fmt")

    response = await client.get("/api/playbook/stream/job_sse_fmt")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    lines = response.text.strip().split("\n")
    data_lines = [line for line in lines if line.startswith("data:")]
    assert len(data_lines) >= 1

    import json

    payload = json.loads(data_lines[0].removeprefix("data:").strip())
    assert payload["type"] in {"run_started", "agent_start", "tool_call"}
    assert "trace" in payload or payload.get("job_id") == "job_sse_fmt"


@pytest.mark.asyncio
async def test_demo_list_includes_seeded_aapl(client):
    response = await client.get("/api/playbook/demo")
    assert response.status_code == 200
    tickers = response.json()["tickers"]
    assert "AAPL" in tickers
