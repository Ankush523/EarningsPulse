"""Map internal trace events to SSE event types."""

from __future__ import annotations

from typing import Any

from app.models.trace import TraceEvent, TraceEventType

SSE_AGENT_START = "agent_start"
SSE_TOOL_CALL = "tool_call"
SSE_AGENT_COMPLETE = "agent_complete"
SSE_PLAYBOOK_READY = "playbook_ready"
SSE_ERROR = "error"
SSE_RUN_STARTED = "run_started"
SSE_RUN_COMPLETED = "run_completed"


def trace_event_to_sse(event: dict[str, Any] | TraceEvent) -> dict[str, Any]:
    """Convert a trace event dict or model to an SSE payload."""
    if isinstance(event, TraceEvent):
        data = event.model_dump(mode="json")
    else:
        data = dict(event)

    event_type = data.get("event_type", "")
    sse_type = _map_event_type(event_type)

    return {
        "type": sse_type,
        "job_id": data.get("job_id"),
        "timestamp": data.get("timestamp"),
        "agent_name": data.get("agent_name"),
        "tool_name": data.get("tool_name"),
        "message": data.get("message"),
        "latency_ms": data.get("latency_ms"),
        "error": data.get("error"),
        "input_summary": data.get("input_summary"),
        "output_summary": data.get("output_summary"),
        "trace": data,
    }


def _map_event_type(event_type: str) -> str:
    mapping = {
        TraceEventType.RUN_STARTED.value: SSE_RUN_STARTED,
        TraceEventType.RUN_COMPLETED.value: SSE_RUN_COMPLETED,
        TraceEventType.RUN_FAILED.value: SSE_ERROR,
        TraceEventType.AGENT_STARTED.value: SSE_AGENT_START,
        TraceEventType.AGENT_COMPLETED.value: SSE_AGENT_COMPLETE,
        TraceEventType.TOOL_CALL_STARTED.value: SSE_TOOL_CALL,
        TraceEventType.TOOL_CALL_COMPLETED.value: SSE_TOOL_CALL,
        TraceEventType.TOOL_CALL_FAILED.value: SSE_ERROR,
        TraceEventType.CONFIDENCE_UPDATED.value: SSE_TOOL_CALL,
    }
    return mapping.get(event_type, SSE_TOOL_CALL)


def playbook_ready_event(job_id: str, ticker: str) -> dict[str, Any]:
    return {
        "type": SSE_PLAYBOOK_READY,
        "job_id": job_id,
        "ticker": ticker,
        "message": "Playbook generation completed",
    }


def error_event(job_id: str, message: str) -> dict[str, Any]:
    return {
        "type": SSE_ERROR,
        "job_id": job_id,
        "message": message,
        "error": message,
    }
