"""Playbook generation API routes."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, Response, StreamingResponse

from app.api.deps import get_job_runner, get_job_store
from app.api.rate_limit import client_key, playbook_rate_limiter
from app.models.playbook import (
    JobStatus,
    PlaybookGenerateRequest,
    PlaybookGenerateResponse,
    PlaybookStatus,
)
from app.services.job_store import JobStore
from app.services.playbook_runner import PlaybookJobRunner
from app.services.sse_events import error_event, trace_event_to_sse
from app.services.trace_store import TraceStore

router = APIRouter(prefix="/playbook", tags=["playbook"])


@router.post("/generate", response_model=PlaybookGenerateResponse)
async def generate_playbook(
    body: PlaybookGenerateRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    runner: PlaybookJobRunner = Depends(get_job_runner),
    store: JobStore = Depends(get_job_store),
) -> PlaybookGenerateResponse:
    """Start asynchronous playbook generation for a ticker."""
    await playbook_rate_limiter.check(client_key(request))

    earnings_date = body.earnings_date.isoformat() if body.earnings_date else None
    job_id = await runner.start_job(
        body.ticker,
        earnings_date=earnings_date,
    )

    background_tasks.add_task(runner.execute_job, job_id)

    return PlaybookGenerateResponse(
        job_id=job_id,
        ticker=body.ticker.upper(),
        status=PlaybookStatus.PENDING.value,
        stream_url=f"/api/playbook/stream/{job_id}",
    )


@router.get("/{job_id}/export/json")
async def export_playbook_json(
    job_id: str,
    store: JobStore = Depends(get_job_store),
) -> Response:
    """Download completed playbook as JSON."""
    job = await store.get(job_id)
    if job.playbook is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playbook not available for export",
        )

    filename = f"earningspulse-{job.ticker.lower()}-{job_id}.json"
    content = job.playbook.model_dump_json(indent=2)
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{job_id}/export/bundle")
async def export_playbook_bundle(
    job_id: str,
    store: JobStore = Depends(get_job_store),
) -> JSONResponse:
    """Download playbook + PRISM trace as a single JSON bundle."""
    job = await store.get(job_id)
    if job.playbook is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playbook not available for export",
        )

    trace_store = TraceStore(store=store)
    trace_log = trace_store.build_trace_log(job)
    bundle = {
        "exported_at": datetime.now(UTC).isoformat(),
        "job_id": job_id,
        "ticker": job.ticker,
        "playbook": job.playbook.model_dump(mode="json"),
        "trace": trace_log.model_dump(mode="json"),
    }
    filename = f"earningspulse-{job.ticker.lower()}-{job_id}-bundle.json"
    return JSONResponse(
        content=bundle,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/stream/{job_id}")
async def stream_playbook_events(
    job_id: str,
    store: JobStore = Depends(get_job_store),
) -> StreamingResponse:
    """Server-Sent Events stream of agent progress and trace data."""
    job = await store.get(job_id)

    async def event_generator() -> AsyncIterator[str]:
        # Replay events that occurred before the client connected
        for event in job.trace_events:
            yield _format_sse(trace_event_to_sse(event))

        if job.status in {PlaybookStatus.COMPLETED, PlaybookStatus.FAILED}:
            if job.status == PlaybookStatus.COMPLETED:
                yield _format_sse(
                    {
                        "type": "playbook_ready",
                        "job_id": job_id,
                        "ticker": job.ticker,
                        "message": "Playbook already completed",
                    }
                )
            elif job.error:
                yield _format_sse(error_event(job_id, job.error))
            return

        while True:
            try:
                event = await asyncio.wait_for(job.event_queue.get(), timeout=120.0)
            except TimeoutError:
                yield _format_sse(
                    {
                        "type": "heartbeat",
                        "job_id": job_id,
                        "message": "keep-alive",
                    }
                )
                refreshed = await store.get(job_id)
                if refreshed.status in {
                    PlaybookStatus.COMPLETED,
                    PlaybookStatus.FAILED,
                }:
                    break
                continue

            yield _format_sse(event)

            if event.get("type") in {"playbook_ready", "error"}:
                break

            refreshed = await store.get(job_id)
            if refreshed.status in {PlaybookStatus.COMPLETED, PlaybookStatus.FAILED}:
                if refreshed.status == PlaybookStatus.COMPLETED:
                    yield _format_sse(
                        {
                            "type": "playbook_ready",
                            "job_id": job_id,
                            "ticker": refreshed.ticker,
                        }
                    )
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{job_id}", response_model=JobStatus)
async def get_playbook_job(
    job_id: str,
    store: JobStore = Depends(get_job_store),
) -> JobStatus:
    """Fetch job status and completed playbook."""
    job = await store.get(job_id)
    return JobStatus(
        job_id=job.job_id,
        ticker=job.ticker,
        status=job.status,
        playbook=job.playbook,
        error=job.error,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )


def _format_sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, default=str)}\n\n"
