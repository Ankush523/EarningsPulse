"""Trace event helpers for agent observability."""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from app.models.trace import TraceEvent, TraceEventType


def new_event_id() -> str:
    return f"evt_{uuid.uuid4().hex[:12]}"


def make_trace_event(
    job_id: str,
    event_type: TraceEventType,
    message: str,
    *,
    agent_name: str | None = None,
    tool_name: str | None = None,
    input_summary: dict[str, Any] | None = None,
    output_summary: dict[str, Any] | None = None,
    latency_ms: int | None = None,
    error: str | None = None,
    retry_attempt: int | None = None,
) -> TraceEvent:
    return TraceEvent(
        event_id=new_event_id(),
        job_id=job_id,
        event_type=event_type,
        message=message,
        agent_name=agent_name,
        tool_name=tool_name,
        input_summary=input_summary,
        output_summary=output_summary,
        latency_ms=latency_ms,
        error=error,
        retry_attempt=retry_attempt,
    )


def trace_to_dict(event: TraceEvent) -> dict[str, Any]:
    return event.model_dump(mode="json")


@asynccontextmanager
async def traced_tool(
    job_id: str,
    agent_name: str,
    tool_name: str,
    input_summary: dict[str, Any] | None = None,
) -> AsyncIterator[list[TraceEvent]]:
    """Context manager that yields a list to append trace events during tool execution."""
    events: list[TraceEvent] = []
    started = time.perf_counter()
    events.append(
        make_trace_event(
            job_id,
            TraceEventType.TOOL_CALL_STARTED,
            f"{agent_name} calling {tool_name}",
            agent_name=agent_name,
            tool_name=tool_name,
            input_summary=input_summary,
        )
    )
    error: str | None = None
    try:
        yield events
    except Exception as exc:
        error = str(exc)
        events.append(
            make_trace_event(
                job_id,
                TraceEventType.TOOL_CALL_FAILED,
                f"{tool_name} failed: {exc}",
                agent_name=agent_name,
                tool_name=tool_name,
                error=error,
                latency_ms=int((time.perf_counter() - started) * 1000),
            )
        )
        raise
    else:
        events.append(
            make_trace_event(
                job_id,
                TraceEventType.TOOL_CALL_COMPLETED,
                f"{tool_name} completed",
                agent_name=agent_name,
                tool_name=tool_name,
                latency_ms=int((time.perf_counter() - started) * 1000),
            )
        )
