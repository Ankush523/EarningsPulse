"""Background playbook generation with streaming trace events."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from app.agents.orchestrator import PlaybookOrchestrator
from app.agents.trace_utils import make_trace_event, trace_to_dict
from app.config import Settings, get_settings
from app.models.playbook import PlaybookStatus
from app.models.trace import TraceEventType
from app.services.job_store import JobStore, job_store
from app.services.prism_client import PrismClient, get_prism_client
from app.services.sse_events import error_event, playbook_ready_event, trace_event_to_sse
from app.services.trace_store import TraceStore

logger = logging.getLogger(__name__)


class PlaybookJobRunner:
    """Execute playbook generation jobs and publish SSE events."""

    def __init__(
        self,
        store: JobStore | None = None,
        orchestrator: PlaybookOrchestrator | None = None,
        settings: Settings | None = None,
        prism_client: PrismClient | None = None,
        trace_store: TraceStore | None = None,
    ):
        self._store = store or job_store
        self._settings = settings or get_settings()
        self._orchestrator = orchestrator or PlaybookOrchestrator(settings=self._settings)
        self._prism = prism_client or get_prism_client()
        self._trace_store = trace_store or TraceStore(store=self._store, settings=self._settings)

    async def start_job(
        self,
        ticker: str,
        *,
        job_id: str | None = None,
        earnings_date: str | None = None,
    ) -> str:
        """Create a job and schedule background execution."""
        normalized = ticker.upper().strip()
        job_id = job_id or f"job_{uuid.uuid4().hex[:12]}"
        await self._store.create(job_id, normalized, earnings_date=earnings_date)
        return job_id

    async def execute_job(self, job_id: str) -> None:
        """Run the agent pipeline for an existing job."""
        job = await self._store.get(job_id)
        await self._store.update_status(job_id, PlaybookStatus.RUNNING)

        started = time.perf_counter()
        seen_trace_ids: set[str] = set()

        try:
            async for update in self._orchestrator.astream(
                job.ticker,
                job_id=job_id,
                earnings_date=job.earnings_date,
            ):
                await self._publish_update(job_id, update, seen_trace_ids)

            final_job = await self._store.get(job_id)
            playbook = final_job.playbook
            if playbook is None:
                raise RuntimeError("Pipeline finished without a playbook")

            elapsed = int((time.perf_counter() - started) * 1000)
            playbook.metadata.generation_time_ms = elapsed

            completed_event = trace_to_dict(
                make_trace_event(
                    job_id,
                    TraceEventType.RUN_COMPLETED,
                    f"Playbook generation completed for {job.ticker}",
                    latency_ms=elapsed,
                    output_summary={"ticker": job.ticker},
                )
            )
            if completed_event["event_id"] not in seen_trace_ids:
                seen_trace_ids.add(completed_event["event_id"])
                await self._store.append_trace(job_id, completed_event)
                await self._store.publish_event(job_id, trace_event_to_sse(completed_event))
                await self._prism.emit(completed_event)

            ready = playbook_ready_event(job_id, job.ticker)
            await self._store.publish_event(job_id, ready)
            await self._store.update_status(job_id, PlaybookStatus.COMPLETED, playbook=playbook)
            await self._finalize_trace(job_id)
        except Exception as exc:
            logger.exception("Job %s failed: %s", job_id, exc)
            fail_event = trace_to_dict(
                make_trace_event(
                    job_id,
                    TraceEventType.RUN_FAILED,
                    f"Playbook generation failed: {exc}",
                    error=str(exc),
                    latency_ms=int((time.perf_counter() - started) * 1000),
                )
            )
            await self._store.append_trace(job_id, fail_event)
            await self._store.publish_event(job_id, trace_event_to_sse(fail_event))
            await self._prism.emit(fail_event)
            await self._store.publish_event(job_id, error_event(job_id, str(exc)))
            await self._store.update_status(job_id, PlaybookStatus.FAILED, error=str(exc))
            await self._finalize_trace(job_id)

    async def _finalize_trace(self, job_id: str) -> None:
        """Persist trace log locally and sync to PRISM when configured."""
        try:
            job = await self._store.get(job_id)
            trace_log = self._trace_store.build_trace_log(job)
            await self._trace_store.save_trace_log(trace_log)
            synced = await self._prism.sync_trace_log(trace_log)
            if synced:
                await self._store.mark_prism_synced(job_id, True)
                trace_log.prism_synced = True
        except Exception as exc:
            logger.warning("Trace finalization failed for job %s: %s", job_id, exc)

    async def _publish_update(
        self,
        job_id: str,
        update: dict[str, Any],
        seen_trace_ids: set[str],
    ) -> None:
        """Publish trace events from a LangGraph node update."""
        trace_events = update.get("trace_events") or []
        for raw_event in trace_events:
            event_id = raw_event.get("event_id")
            if event_id and event_id in seen_trace_ids:
                continue
            if event_id:
                seen_trace_ids.add(event_id)
            await self._store.append_trace(job_id, raw_event)
            await self._store.publish_event(job_id, trace_event_to_sse(raw_event))
            await self._prism.emit(raw_event)

        if update.get("playbook") is not None:
            job = await self._store.get(job_id)
            job.playbook = update["playbook"]
