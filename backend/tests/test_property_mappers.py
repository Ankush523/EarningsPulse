"""Property-based checks for deterministic agent mapping helpers."""

from __future__ import annotations

from datetime import UTC, date

import pytest
from app.agents.mappers import (
    _build_scenarios,
    parse_confidence,
    parse_peer_relationship,
    peer_map_to_spillover,
    reaction_analysis_to_summary,
)
from app.models.analysis import (
    EarningsReactionEvent,
    PeerCandidate,
    PeerMapResult,
    ReactionPatternAnalysis,
)
from app.models.playbook import (
    ConfidenceTier,
    PeerRelationship,
    ReactionArchetype,
)
from hypothesis import given, settings
from hypothesis import strategies as st


@settings(max_examples=40)
@given(
    tier=st.sampled_from(list(ConfidenceTier)),
    uppercase=st.booleans(),
)
def test_parse_confidence_round_trips_supported_values(
    tier: ConfidenceTier,
    uppercase: bool,
) -> None:
    text = tier.value.upper() if uppercase else tier.value

    assert parse_confidence(tier) is tier
    assert parse_confidence(text) is tier


@settings(max_examples=40)
@given(
    relationship=st.sampled_from(list(PeerRelationship)),
    uppercase=st.booleans(),
)
def test_parse_peer_relationship_round_trips_supported_values(
    relationship: PeerRelationship,
    uppercase: bool,
) -> None:
    text = relationship.value.upper() if uppercase else relationship.value

    assert parse_peer_relationship(relationship) is relationship
    assert parse_peer_relationship(text) is relationship


@settings(max_examples=50)
@given(archetype=st.sampled_from(list(ReactionArchetype)))
def test_scenario_probabilities_form_a_distribution(
    archetype: ReactionArchetype,
) -> None:
    analysis = ReactionPatternAnalysis(
        ticker="TEST",
        archetype=archetype,
        archetype_description="property analysis",
        events_analyzed=0,
    )

    scenarios = _build_scenarios(analysis)

    assert scenarios
    assert sum(scenario.probability for scenario in scenarios) == pytest.approx(1.0)
    assert all(0 <= scenario.probability <= 1 for scenario in scenarios)


correlations = st.one_of(
    st.sampled_from([-1.0, -0.25, -0.249999, 0.0, 0.249999, 0.25, 1.0]),
    st.floats(min_value=-1, max_value=1, allow_nan=False, allow_infinity=False),
)


@settings(max_examples=60)
@given(correlation=correlations)
def test_peer_mapping_preserves_correlation_and_watch_threshold(
    correlation: float,
) -> None:
    result = PeerMapResult(
        reporting_ticker="AAPL",
        peers=[
            PeerCandidate(
                ticker="MSFT",
                relationship=PeerRelationship.DIRECT_PEER,
                correlation_score=correlation,
                expected_direction="same",
                rationale="property peer",
            )
        ],
    )

    mapped = peer_map_to_spillover(result)

    assert mapped.reporting_ticker == result.reporting_ticker
    assert mapped.peers[0].correlation_score == correlation
    assert mapped.peers[0].watch_flag is (abs(correlation) >= 0.25)


@settings(max_examples=40)
@given(days=st.integers(min_value=0, max_value=30))
def test_reaction_mapping_converts_trading_days_to_minutes(days: int) -> None:
    event_date = date(2026, 1, 2)
    analysis = ReactionPatternAnalysis(
        ticker="AAPL",
        archetype=ReactionArchetype.DIP_THEN_RALLY,
        archetype_description="property analysis",
        events_analyzed=1,
        events=[
            EarningsReactionEvent(
                ticker="AAPL",
                earnings_date=event_date,
                initial_move_pct=0,
                time_to_bottom_days=days,
                pattern=ReactionArchetype.DIP_THEN_RALLY,
            )
        ],
    )

    mapped = reaction_analysis_to_summary(analysis).historical_reactions[0]

    assert mapped.earnings_date.date() == event_date
    assert mapped.earnings_date.tzinfo is UTC
    assert mapped.time_to_bottom_minutes == days * 390
