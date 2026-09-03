"""Tests for SSE event mapping and format."""

from app.agents.trace_utils import make_trace_event, trace_to_dict
from app.models.trace import TraceEventType
from app.services.sse_events import (
    SSE_AGENT_COMPLETE,
    SSE_AGENT_START,
    SSE_ERROR,
    SSE_PLAYBOOK_READY,
    SSE_RUN_COMPLETED,
    SSE_RUN_STARTED,
    SSE_TOOL_CALL,
    error_event,
    playbook_ready_event,
    trace_event_to_sse,
)


def test_trace_event_to_sse_agent_started():
    event = trace_to_dict(
        make_trace_event(
            "job_1",
            TraceEventType.AGENT_STARTED,
            "Research agent started",
            agent_name="research",
        )
    )
    sse = trace_event_to_sse(event)
    assert sse["type"] == SSE_AGENT_START
    assert sse["job_id"] == "job_1"
    assert sse["agent_name"] == "research"
    assert sse["trace"]["event_type"] == "agent_started"


def test_trace_event_to_sse_tool_call():
    event = trace_to_dict(
        make_trace_event(
            "job_1",
            TraceEventType.TOOL_CALL_COMPLETED,
            "tavily_search completed",
            agent_name="research",
            tool_name="tavily_search",
            latency_ms=250,
        )
    )
    sse = trace_event_to_sse(event)
    assert sse["type"] == SSE_TOOL_CALL
    assert sse["tool_name"] == "tavily_search"
    assert sse["latency_ms"] == 250


def test_trace_event_to_sse_run_lifecycle():
    started = trace_event_to_sse(
        trace_to_dict(
            make_trace_event(
                "job_2",
                TraceEventType.RUN_STARTED,
                "Started",
            )
        )
    )
    completed = trace_event_to_sse(
        trace_to_dict(
            make_trace_event(
                "job_2",
                TraceEventType.RUN_COMPLETED,
                "Completed",
                latency_ms=900,
            )
        )
    )
    assert started["type"] == SSE_RUN_STARTED
    assert completed["type"] == SSE_RUN_COMPLETED


def test_trace_event_to_sse_failure_maps_to_error():
    event = trace_to_dict(
        make_trace_event(
            "job_3",
            TraceEventType.RUN_FAILED,
            "Failed",
            error="timeout",
        )
    )
    assert trace_event_to_sse(event)["type"] == SSE_ERROR


def test_playbook_ready_event_format():
    event = playbook_ready_event("job_done", "AAPL")
    assert event["type"] == SSE_PLAYBOOK_READY
    assert event["job_id"] == "job_done"
    assert event["ticker"] == "AAPL"


def test_error_event_format():
    event = error_event("job_fail", "Service unavailable")
    assert event["type"] == SSE_ERROR
    assert event["error"] == "Service unavailable"


def test_sse_payload_includes_prism_trace_block():
    event = trace_to_dict(
        make_trace_event(
            "job_4",
            TraceEventType.AGENT_COMPLETED,
            "Forecast completed",
            agent_name="forecast",
            output_summary={"beat_probability": 0.5},
        )
    )
    sse = trace_event_to_sse(event)
    assert sse["type"] == SSE_AGENT_COMPLETE
    assert "trace" in sse
    assert sse["trace"]["event_id"]
