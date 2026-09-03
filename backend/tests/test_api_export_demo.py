"""Tests for demo cache and export endpoints."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from app.main import app
from app.models.playbook import PlaybookStatus
from app.services.demo_store import DemoCacheEntry, DemoStore
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


@pytest.fixture
def demo_dir(tmp_path: Path) -> Path:
    return tmp_path / "demo"


@pytest.fixture
def seeded_demo(demo_dir: Path):
    playbook = _sample_playbook("demo_aapl")
    entry = DemoCacheEntry(
        ticker="AAPL",
        job_id="demo_aapl",
        playbook=playbook,
        source="test",
    )
    store = DemoStore()
    store._demo_dir = demo_dir  # noqa: SLF001
    path = store.save(entry)
    return store, path


@pytest.mark.asyncio
async def test_list_demo_tickers(client, seeded_demo):
    store, _ = seeded_demo
    from app.api.routes import demo as demo_routes

    demo_routes.demo_store._demo_dir = store.demo_dir  # noqa: SLF001

    response = await client.get("/api/playbook/demo")
    assert response.status_code == 200
    assert "AAPL" in response.json()["tickers"]


@pytest.mark.asyncio
async def test_load_demo_playbook(client, seeded_demo):
    store, _ = seeded_demo
    from app.api.routes import demo as demo_routes

    demo_routes.demo_store._demo_dir = store.demo_dir  # noqa: SLF001

    response = await client.post("/api/playbook/demo/AAPL")
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == "demo_aapl"
    assert data["demo"] is True
    assert data["status"] == "completed"

    job = await job_store.get("demo_aapl")
    assert job.status == PlaybookStatus.COMPLETED
    assert job.playbook is not None


@pytest.mark.asyncio
async def test_load_demo_not_found(client, demo_dir):
    from app.api.routes import demo as demo_routes

    demo_routes.demo_store._demo_dir = demo_dir  # noqa: SLF001
    demo_dir.mkdir(parents=True, exist_ok=True)

    response = await client.post("/api/playbook/demo/ZZZZ")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_export_playbook_json(client):
    job = await job_store.create("job_export", "AAPL")
    playbook = _sample_playbook("job_export")
    job.status = PlaybookStatus.COMPLETED
    job.playbook = playbook
    job.completed_at = datetime.now(UTC)

    response = await client.get("/api/playbook/job_export/export/json")
    assert response.status_code == 200
    assert "attachment" in response.headers.get("content-disposition", "")
    assert response.json()["executive_summary"]["ticker"] == "AAPL"


@pytest.mark.asyncio
async def test_export_playbook_bundle(client):
    job = await job_store.create("job_bundle", "NVDA")
    playbook = _sample_playbook("job_bundle")
    job.status = PlaybookStatus.COMPLETED
    job.playbook = playbook
    job.completed_at = datetime.now(UTC)
    await job_store.append_trace(
        "job_bundle",
        {
            "event_id": "evt_1",
            "job_id": "job_bundle",
            "event_type": "run_started",
            "message": "Started",
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )

    response = await client.get("/api/playbook/job_bundle/export/bundle")
    assert response.status_code == 200
    data = response.json()
    assert data["playbook"]["executive_summary"]["ticker"] == "AAPL"
    assert "trace" in data
    assert len(data["trace"]["events"]) >= 1


@pytest.mark.asyncio
async def test_export_not_ready(client):
    await job_store.create("job_pending", "MSFT")
    response = await client.get("/api/playbook/job_pending/export/json")
    assert response.status_code == 404
