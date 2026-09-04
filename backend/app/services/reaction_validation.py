"""Out-of-sample validation to detect overfitting in reaction pattern analysis."""

from __future__ import annotations

from collections import Counter

from app.models.analysis import EarningsReactionEvent, ValidationSummary


def validate_reaction_patterns(
    events: list[EarningsReactionEvent],
    *,
    train_ratio: float = 0.7,
    min_test_events: int = 3,
) -> ValidationSummary | None:
    """
    Chronological train/test split for rule-based archetype stability.

    Measures whether the dominant pattern learned on older quarters still
    describes recent earnings reactions — a practical overfitting check.
    """
    if len(events) < 6:
        return None

    ordered = sorted(events, key=lambda event: event.earnings_date)
    split_idx = max(3, int(len(ordered) * train_ratio))
    if len(ordered) - split_idx < min_test_events:
        split_idx = len(ordered) - min_test_events

    train = ordered[:split_idx]
    test = ordered[split_idx:]
    if not test:
        return None

    train_counts = Counter(event.pattern for event in train)
    test_counts = Counter(event.pattern for event in test)
    train_dominant = train_counts.most_common(1)[0][0]
    test_matches = sum(1 for event in test if event.pattern == train_dominant)
    match_rate = round(test_matches / len(test), 4)

    train_share = train_counts[train_dominant] / len(train)
    test_share = test_counts.get(train_dominant, 0) / len(test)
    drift = abs(train_share - test_share)

    if match_rate >= 0.5 and drift <= 0.25:
        risk = "low"
        reliable = True
        summary = (
            f"Recent {len(test)} quarters align with the {train_dominant.value} pattern "
            f"seen in older data ({match_rate * 100:.0f}% match)."
        )
    elif match_rate >= 0.35 or drift <= 0.35:
        risk = "medium"
        reliable = True
        summary = (
            f"Pattern is mostly stable but recent quarters show some drift "
            f"({match_rate * 100:.0f}% match on holdout set)."
        )
    else:
        risk = "high"
        reliable = False
        summary = (
            f"Recent reactions diverge from the historical pattern "
            f"({match_rate * 100:.0f}% holdout match) — treat scenarios cautiously."
        )

    return ValidationSummary(
        train_events=len(train),
        test_events=len(test),
        train_dominant_archetype=train_dominant,
        test_pattern_match_rate=match_rate,
        pattern_drift=round(drift, 4),
        overfitting_risk=risk,
        is_reliable=reliable,
        summary=summary,
    )
