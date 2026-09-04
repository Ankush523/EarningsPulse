"""Property tests for reaction classification and calendar helpers."""

from datetime import date
from statistics import mean, median

import pytest
from app.models.analysis import EarningsReactionEvent
from app.models.playbook import ReactionArchetype, ReportOutcome
from app.services.earnings_calendar import EarningsCalendarService
from app.services.reaction_analyzer import VOLATILITY_BAND_PCT, ReactionAnalyzer
from hypothesis import given, settings
from hypothesis import strategies as st

finite_percentages = st.floats(
    min_value=-100,
    max_value=100,
    allow_nan=False,
    allow_infinity=False,
    allow_subnormal=False,
)
optional_percentages = st.one_of(st.none(), finite_percentages)


@st.composite
def reaction_events(draw: st.DrawFn) -> list[EarningsReactionEvent]:
    raw_events = draw(
        st.lists(
            st.tuples(
                st.integers(min_value=1, max_value=365),
                st.one_of(st.none(), st.sampled_from(list(ReportOutcome))),
                st.integers(min_value=-50, max_value=50),
                st.one_of(st.none(), st.integers(min_value=-50, max_value=50)),
                st.one_of(st.none(), st.integers(min_value=-50, max_value=50)),
                st.sampled_from(list(ReactionArchetype)),
            ),
            min_size=1,
            max_size=10,
            unique_by=lambda event: event[0],
        )
    )
    return [
        EarningsReactionEvent(
            ticker="ABC",
            earnings_date=date.fromordinal(date(2024, 1, 1).toordinal() + day_offset),
            report_outcome=outcome,
            initial_move_pct=initial_move,
            dip_pct=dip,
            recovery_pct=recovery,
            pattern=pattern,
        )
        for day_offset, outcome, initial_move, dip, recovery, pattern in raw_events
    ]


@settings(max_examples=100, deadline=None)
@given(
    initial_move_pct=finite_percentages,
    dip_pct=optional_percentages,
    recovery_pct=optional_percentages,
)
def test_miss_classification_depends_only_on_initial_move(initial_move_pct, dip_pct, recovery_pct):
    result = ReactionAnalyzer.classify_single_reaction(
        outcome=ReportOutcome.MISS,
        initial_move_pct=initial_move_pct,
        dip_pct=dip_pct,
        recovery_pct=recovery_pct,
    )
    expected = (
        ReactionArchetype.VOLATILITY_PIN
        if abs(initial_move_pct) <= VOLATILITY_BAND_PCT
        else ReactionArchetype.GAP_AND_HOLD
    )

    assert result == expected


@settings(max_examples=100, deadline=None)
@given(finite_percentages)
def test_outcome_from_move_partitions_the_thresholds(initial_move_pct):
    result = ReactionAnalyzer._outcome_from_move(initial_move_pct)
    if initial_move_pct > 1.0:
        assert result == ReportOutcome.BEAT
    elif initial_move_pct < -1.0:
        assert result == ReportOutcome.MISS
    else:
        assert result == ReportOutcome.INLINE


@settings(max_examples=100, deadline=None)
@given(reaction_events())
def test_aggregate_events_is_order_independent_and_matches_summary_statistics(events):
    analyzer = ReactionAnalyzer()
    result = analyzer.aggregate_events(" abc ", events)
    reversed_result = analyzer.aggregate_events(" abc ", list(reversed(events)))

    positive = [
        event
        for event in events
        if event.report_outcome in {ReportOutcome.BEAT, ReportOutcome.INLINE}
        or event.initial_move_pct > 0
    ]
    dipped = [event for event in positive if event.dip_pct is not None and event.dip_pct <= -0.5]
    dip_values = [event.dip_pct for event in dipped if event.dip_pct is not None]
    recovery_values = [
        event.recovery_pct
        for event in positive
        if event.recovery_pct is not None and event.recovery_pct > 0
    ]

    assert result.ticker == "ABC"
    assert result.events == sorted(events, key=lambda event: event.earnings_date, reverse=True)
    assert result.archetype == reversed_result.archetype
    assert result.events == reversed_result.events
    assert result.pattern_counts == reversed_result.pattern_counts
    assert result.avg_dip_pct == reversed_result.avg_dip_pct
    assert result.avg_recovery_pct == reversed_result.avg_recovery_pct
    assert result.dip_frequency_on_positive == reversed_result.dip_frequency_on_positive
    assert result.expected_dip_zone == reversed_result.expected_dip_zone
    assert result.avg_dip_pct == (pytest.approx(round(mean(dip_values), 4)) if dip_values else None)
    assert result.avg_recovery_pct == (
        pytest.approx(round(mean(recovery_values), 4)) if recovery_values else None
    )
    assert result.dip_frequency_on_positive == (
        pytest.approx(round(len(dipped) / len(positive), 4)) if positive else None
    )
    assert result.expected_dip_zone == (
        {
            "min": round(min(dip_values), 4),
            "max": round(max(dip_values), 4),
            "median": round(median(dip_values), 4),
        }
        if dip_values
        else None
    )


@settings(max_examples=100, deadline=None)
@given(st.dates(min_value=date(1970, 1, 1), max_value=date(2100, 12, 31)))
def test_period_helpers_agree_for_valid_calendar_dates(value):
    period = value.isoformat()

    assert EarningsCalendarService._parse_period(period) == value
    assert EarningsCalendarService._extract_year(period) == value.year
    assert EarningsCalendarService._extract_quarter(period) == ((value.month - 1) // 3) + 1


@settings(max_examples=60, deadline=None)
@given(
    canonical_and_alias=st.sampled_from(
        [
            ("bmo", "bmo"),
            ("before market open", "bmo"),
            ("am", "bmo"),
            ("amc", "amc"),
            ("after market close", "amc"),
            ("pm", "amc"),
            ("after hours", "amc"),
        ]
    ),
    uppercase=st.booleans(),
    left_padding=st.text(alphabet=" \t", max_size=3),
    right_padding=st.text(alphabet=" \t", max_size=3),
)
def test_report_time_aliases_are_case_and_whitespace_insensitive(
    canonical_and_alias, uppercase, left_padding, right_padding
):
    alias, canonical = canonical_and_alias
    rendered = alias.upper() if uppercase else alias

    assert (
        EarningsCalendarService._normalize_report_time(f"{left_padding}{rendered}{right_padding}")
        == canonical
    )
