"""Model validation tests for Phase 0."""

import pytest
from app.models import (
    AgentState,
    ExecutiveSummary,
    PlaybookGenerateRequest,
    ReactionArchetype,
    TraceEvent,
    TraceEventType,
)
from pydantic import ValidationError


def test_playbook_generate_request_valid():
    req = PlaybookGenerateRequest(ticker="AAPL")
    assert req.ticker == "AAPL"


def test_playbook_generate_request_invalid_ticker():
    with pytest.raises(ValidationError):
        PlaybookGenerateRequest(ticker="INVALID123")


def test_trace_event_creation():
    event = TraceEvent(
        event_id="evt-1",
        job_id="job-1",
        event_type=TraceEventType.RUN_STARTED,
        message="Run started for AAPL",
    )
    assert event.event_type == TraceEventType.RUN_STARTED


def test_executive_summary_probabilities():
    summary = ExecutiveSummary(
        ticker="NVDA",
        beat_probability=0.6,
        inline_probability=0.25,
        miss_probability=0.15,
        primary_pattern=ReactionArchetype.DIP_THEN_RALLY,
        primary_pattern_description="Historical dip-then-rally pattern",
        overall_confidence="medium",
        top_drivers=["Data center demand", "Guidance tone"],
    )
    assert summary.beat_probability == 0.6
    assert summary.primary_pattern == ReactionArchetype.DIP_THEN_RALLY


def test_agent_state_typed_dict():
    state: AgentState = {
        "job_id": "job-1",
        "ticker": "AAPL",
        "trace_events": [],
        "errors": [],
        "messages": [],
        "status": "pending",
    }
    assert state["ticker"] == "AAPL"
