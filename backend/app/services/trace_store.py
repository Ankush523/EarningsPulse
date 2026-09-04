"""Local trace log persistence and TraceLog assembly."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.config import Settings, get_settings
from app.models.agent_state import serialize_trace_events
from app.models.trace import TraceEvent, TraceEventType, TraceLog
from app.services.job_store import JobNotFoundError, JobStore, PlaybookJob, job_store

logger = logging.getLogger(__name__)


class TraceStore:
    """Persist and retrieve PRISM-compatible trace logs for playbook jobs."""

    def __init__(
        self,
        store: JobStore | None = None,
        settings: Settings | None = None,
    ):
        self._store = store or job_store
        self._settings = settings or get_settings()
        self._log_dir = Path(self._settings.trace_log_dir)

    def build_trace_log(self, job: PlaybookJob) -> TraceLog:
        """Assemble a TraceLog from a playbook job."""
        events = serialize_trace_events(job.trace_events)
        total_latency_ms = _resolve_total_latency_ms(events, job)

        return TraceLog(
            job_id=job.job_id,
            ticker=job.ticker,
            events=events,
            started_at=job.created_at,
            completed_at=job.completed_at,
            total_latency_ms=total_latency_ms,
            prism_synced=job.prism_synced,
        )

    async def get_trace_log(self, job_id: str) -> TraceLog:
        """Return trace log from memory or local JSON fallback."""
        try:
            job = await self._store.get(job_id)
            return self.build_trace_log(job)
        except JobNotFoundError:
            persisted = self._load_from_disk(job_id)
            if persisted is not None:
                return persisted
            raise

    async def save_trace_log(self, trace_log: TraceLog) -> Path:
        """Persist trace log to local JSON (always, for audit/export)."""
        self._log_dir.mkdir(parents=True, exist_ok=True)
        path = self._log_dir / f"{trace_log.job_id}.json"
        payload = trace_log.model_dump(mode="json")
        path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        logger.debug("Saved trace log to %s", path)
        return path

    def _load_from_disk(self, job_id: str) -> TraceLog | None:
        path = self._log_dir / f"{job_id}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return TraceLog.model_validate(data)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("Failed to load trace log %s: %s", path, exc)
            return None


def _resolve_total_latency_ms(events: list[TraceEvent], job: PlaybookJob) -> int | None:
    for event in reversed(events):
        if event.event_type == TraceEventType.RUN_COMPLETED and event.latency_ms is not None:
            return event.latency_ms
        if event.event_type == TraceEventType.RUN_FAILED and event.latency_ms is not None:
            return event.latency_ms

    if job.completed_at and job.created_at:
        delta = job.completed_at - job.created_at
        return max(int(delta.total_seconds() * 1000), 0)
    return None


def trace_event_to_prism_step(event: TraceEvent) -> dict[str, Any]:
    """Map an internal trace event to a PRISM trajectory step."""
    step_type = "reasoning"
    label = event.message

    if event.event_type in {
        TraceEventType.TOOL_CALL_STARTED,
        TraceEventType.TOOL_CALL_COMPLETED,
        TraceEventType.TOOL_CALL_FAILED,
    }:
        step_type = "tool_call"
        label = event.tool_name or event.message
    elif event.event_type == TraceEventType.RUN_COMPLETED:
        step_type = "final_answer"
    elif event.event_type == TraceEventType.RUN_FAILED:
        step_type = "error"

    step: dict[str, Any] = {
        "step_type": step_type,
        "label": label,
        "duration_ms": event.latency_ms or 0,
    }

    if event.agent_name:
        step["agent_name"] = event.agent_name
    if event.tool_name:
        step["tool_name"] = event.tool_name
    if event.input_summary:
        step["input_summary"] = _stringify_summary(event.input_summary)
    if event.output_summary:
        step["output_summary"] = _stringify_summary(event.output_summary)
    if event.error:
        step["error"] = event.error
        step["status"] = "error"

    step["metadata"] = {
        "event_id": event.event_id,
        "event_type": event.event_type.value,
        "timestamp": event.timestamp.isoformat(),
    }
    return step


def _stringify_summary(summary: dict[str, Any]) -> str:
    if len(summary) == 1 and isinstance(next(iter(summary.values())), str):
        return str(next(iter(summary.values())))
    return json.dumps(summary, default=str)
