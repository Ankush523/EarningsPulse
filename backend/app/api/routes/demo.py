"""Demo playbook API routes."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.deps import get_job_store
from app.models.playbook import PlaybookGenerateResponse, PlaybookStatus
from app.services.demo_store import DemoStore, demo_store
from app.services.job_store import JobNotFoundError, JobStore

router = APIRouter(prefix="/playbook/demo", tags=["demo"])


class DemoListResponse(BaseModel):
    tickers: list[str]


class DemoLoadResponse(PlaybookGenerateResponse):
    demo: bool = True
    cached: bool = True


def get_demo_store() -> DemoStore:
    return demo_store


@router.get("", response_model=DemoListResponse)
async def list_demo_tickers(
    store: DemoStore = Depends(get_demo_store),
) -> DemoListResponse:
    """List tickers with pre-cached demo playbooks."""
    return DemoListResponse(tickers=store.list_tickers())


@router.post("/{ticker}", response_model=DemoLoadResponse)
async def load_demo_playbook(
    ticker: str,
    demo: DemoStore = Depends(get_demo_store),
    job_store: JobStore = Depends(get_job_store),
) -> DemoLoadResponse:
    """
    Create an instantly-completed job from a pre-cached demo playbook.

    Run `python scripts/seed_demo.py` to populate the demo cache.
    """
    normalized = ticker.upper().strip()
    entry = demo.load(normalized)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No demo cache for {normalized}. "
                "Run: python scripts/seed_demo.py --ticker "
                f"{normalized} (or --offline for mock data)"
            ),
        )

    job_id = entry.job_id

    try:
        job = await job_store.get(job_id)
        job.playbook = entry.playbook
        job.status = PlaybookStatus.COMPLETED
        job.completed_at = datetime.now(UTC)
        job.error = None
    except JobNotFoundError:
        await job_store.create(job_id, normalized)
        await job_store.update_status(
            job_id,
            PlaybookStatus.COMPLETED,
            playbook=entry.playbook,
        )

    if entry.trace_log:
        job = await job_store.get(job_id)
        job.trace_events = [event.model_dump(mode="json") for event in entry.trace_log.events]

    return DemoLoadResponse(
        job_id=job_id,
        ticker=normalized,
        status=PlaybookStatus.COMPLETED.value,
        stream_url=f"/api/playbook/stream/{job_id}",
        demo=True,
        cached=True,
    )
