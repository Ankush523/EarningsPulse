"""In-memory playbook generation job store with SSE event queues."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.models.playbook import Playbook, PlaybookStatus


@dataclass
class PlaybookJob:
    """A single playbook generation job."""

    job_id: str
    ticker: str
    status: PlaybookStatus = PlaybookStatus.PENDING
    playbook: Playbook | None = None
    error: str | None = None
    trace_events: list[dict[str, Any]] = field(default_factory=list)
    event_queue: asyncio.Queue[dict[str, Any]] = field(default_factory=asyncio.Queue)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    earnings_date: str | None = None
    prism_synced: bool = False


class JobNotFoundError(KeyError):
    """Raised when a job_id does not exist in the store."""


class JobStore:
    """Thread-safe in-memory store for playbook jobs."""

    def __init__(self) -> None:
        self._jobs: dict[str, PlaybookJob] = {}
        self._lock = asyncio.Lock()

    async def create(
        self,
        job_id: str,
        ticker: str,
        *,
        earnings_date: str | None = None,
    ) -> PlaybookJob:
        async with self._lock:
            job = PlaybookJob(
                job_id=job_id,
                ticker=ticker.upper(),
                earnings_date=earnings_date,
            )
            self._jobs[job_id] = job
            return job

    async def get(self, job_id: str) -> PlaybookJob:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise JobNotFoundError(job_id)
            return job

    async def update_status(
        self,
        job_id: str,
        status: PlaybookStatus,
        *,
        playbook: Playbook | None = None,
        error: str | None = None,
    ) -> PlaybookJob:
        job = await self.get(job_id)
        job.status = status
        if playbook is not None:
            job.playbook = playbook
        if error is not None:
            job.error = error
        if status in {PlaybookStatus.COMPLETED, PlaybookStatus.FAILED}:
            job.completed_at = datetime.now(UTC)
        return job

    async def mark_prism_synced(self, job_id: str, synced: bool = True) -> None:
        job = await self.get(job_id)
        job.prism_synced = synced

    async def append_trace(self, job_id: str, event: dict[str, Any]) -> None:
        job = await self.get(job_id)
        job.trace_events.append(event)

    async def publish_event(self, job_id: str, event: dict[str, Any]) -> None:
        job = await self.get(job_id)
        await job.event_queue.put(event)

    async def list_jobs(self, limit: int = 50) -> list[PlaybookJob]:
        async with self._lock:
            jobs = sorted(
                self._jobs.values(),
                key=lambda j: j.created_at,
                reverse=True,
            )
            return jobs[:limit]

    async def clear(self) -> None:
        """Clear all jobs — for testing only."""
        async with self._lock:
            self._jobs.clear()


# Application-wide singleton
job_store = JobStore()
