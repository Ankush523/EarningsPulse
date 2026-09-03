"""Trace log API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_trace_store
from app.models.trace import TraceLog
from app.services.trace_store import TraceStore

router = APIRouter(prefix="/trace", tags=["trace"])


@router.get("/{job_id}", response_model=TraceLog)
async def get_job_trace(
    job_id: str,
    trace_store: TraceStore = Depends(get_trace_store),
) -> TraceLog:
    """Return the full PRISM-compatible trace log for a playbook generation job."""
    return await trace_store.get_trace_log(job_id)
