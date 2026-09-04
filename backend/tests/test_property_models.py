"""Property-based checks for validation and model serialization contracts."""

from __future__ import annotations

import re
from datetime import UTC, datetime

import pytest
from app.models.agent_state import serialize_trace_events
from app.models.playbook import PlaybookGenerateRequest
from app.models.trace import TraceEvent, TraceEventType
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

VALID_TICKER_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.-"
INVALID_TICKER_CHARS = "0123456789_ /+$"

json_scalars = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-(2**31), max_value=2**31 - 1),
    st.floats(allow_nan=False, allow_infinity=False, width=32),
    st.text(max_size=20),
)
json_values = st.recursive(
    json_scalars,
    lambda children: st.one_of(
        st.lists(children, max_size=4),
        st.dictionaries(st.text(max_size=12), children, max_size=4),
    ),
    max_leaves=12,
)
json_objects = st.dictionaries(st.text(max_size=12), json_values, max_size=5)


@settings(max_examples=60)
@given(st.text(alphabet=VALID_TICKER_CHARS, min_size=1, max_size=10))
def test_ticker_accepts_exactly_the_declared_alphabet(ticker: str) -> None:
    request = PlaybookGenerateRequest(ticker=ticker)

    assert request.ticker == ticker


invalid_tickers = st.one_of(
    st.just(""),
    st.text(alphabet=VALID_TICKER_CHARS, min_size=11, max_size=20),
    st.builds(
        "{}{}{}".format,
        st.text(alphabet=VALID_TICKER_CHARS, max_size=4),
        st.sampled_from(INVALID_TICKER_CHARS),
        st.text(alphabet=VALID_TICKER_CHARS, max_size=4),
    ),
)


@settings(max_examples=60)
@given(invalid_tickers)
def test_ticker_rejects_values_outside_its_language(ticker: str) -> None:
    assert not re.fullmatch(r"[A-Za-z.\-]{1,10}", ticker)

    with pytest.raises(ValidationError):
        PlaybookGenerateRequest(ticker=ticker)


@settings(max_examples=50)
@given(
    event_type=st.sampled_from(list(TraceEventType)),
    input_summary=st.one_of(st.none(), json_objects),
    output_summary=st.one_of(st.none(), json_objects),
    metadata=json_objects,
)
def test_trace_event_json_round_trip_preserves_data(
    event_type: TraceEventType,
    input_summary: dict[str, object] | None,
    output_summary: dict[str, object] | None,
    metadata: dict[str, object],
) -> None:
    event = TraceEvent(
        event_id="evt_property",
        job_id="job_property",
        event_type=event_type,
        timestamp=datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC),
        message="property event",
        input_summary=input_summary,
        output_summary=output_summary,
        metadata=metadata,
    )

    restored = TraceEvent.model_validate_json(event.model_dump_json())

    assert restored == event


@settings(max_examples=40)
@given(st.lists(json_objects, max_size=8))
def test_serialize_trace_events_accepts_any_mix_of_models_and_dicts(
    metadata_items: list[dict[str, object]],
) -> None:
    models = [
        TraceEvent(
            event_id=f"evt_{index}",
            job_id="job_property",
            event_type=TraceEventType.RUN_STARTED,
            timestamp=datetime(2026, 1, 2, tzinfo=UTC),
            message="event",
            metadata=metadata,
        )
        for index, metadata in enumerate(metadata_items)
    ]
    mixed = [model if index % 2 == 0 else model.model_dump() for index, model in enumerate(models)]

    assert serialize_trace_events(mixed) == models
