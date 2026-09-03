"""Confidence scoring utilities for analysis outputs."""

from __future__ import annotations

from app.models.playbook import ConfidenceTier


def score_from_sample_size(
    sample_size: int,
    *,
    high_threshold: int = 6,
    medium_threshold: int = 3,
) -> ConfidenceTier:
    """Map sample size to a confidence tier."""
    if sample_size >= high_threshold:
        return ConfidenceTier.HIGH
    if sample_size >= medium_threshold:
        return ConfidenceTier.MEDIUM
    return ConfidenceTier.LOW


def score_from_data_quality(
    *,
    sample_size: int,
    has_estimates: bool = False,
    has_correlation: bool = False,
    source_count: int = 1,
) -> ConfidenceTier:
    """
    Composite confidence score from data availability signals.

    Uses the weakest relevant signal to avoid overconfidence.
    """
    tiers: list[ConfidenceTier] = [score_from_sample_size(sample_size)]

    if sample_size == 0:
        return ConfidenceTier.LOW

    if has_correlation and sample_size >= 3:
        tiers.append(ConfidenceTier.HIGH if sample_size >= 5 else ConfidenceTier.MEDIUM)
    elif has_correlation:
        tiers.append(ConfidenceTier.MEDIUM)
    else:
        tiers.append(ConfidenceTier.LOW)

    if has_estimates:
        tiers.append(ConfidenceTier.MEDIUM if sample_size >= 3 else ConfidenceTier.LOW)

    if source_count >= 2:
        tiers.append(ConfidenceTier.MEDIUM)

    return min(tiers, key=_tier_rank)


def combine_confidence(*tiers: ConfidenceTier) -> ConfidenceTier:
    """Return the most conservative (lowest) confidence tier."""
    if not tiers:
        return ConfidenceTier.LOW
    return min(tiers, key=_tier_rank)


def _tier_rank(tier: ConfidenceTier) -> int:
    return {
        ConfidenceTier.HIGH: 3,
        ConfidenceTier.MEDIUM: 2,
        ConfidenceTier.LOW: 1,
    }[tier]
