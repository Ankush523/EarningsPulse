"""PRISM-compatible trace event schemas."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TraceEventType(str, Enum):
    RUN_STARTED = "run_started"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    TOOL_CALL_STARTED = "tool_call_started"
    TOOL_CALL_COMPLETED = "tool_call_completed"
    TOOL_CALL_FAILED = "tool_call_failed"
    CONFIDENCE_UPDATED = "confidence_updated"


class TraceEvent(BaseModel):
    """A single observability event emitted during agent execution."""

    event_id: str
    job_id: str
    event_type: TraceEventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    agent_name: str | None = None
    tool_name: str | None = None
    message: str
    input_summary: dict[str, Any] | None = None
    output_summary: dict[str, Any] | None = None
    latency_ms: int | None = None
    error: str | None = None
    retry_attempt: int | None = None
    confidence_before: str | None = None
    confidence_after: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TraceLog(BaseModel):
    """Complete trace log for a playbook generation job."""

    job_id: str
    ticker: str
    events: list[TraceEvent] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    total_latency_ms: int | None = None
    prism_synced: bool = False
