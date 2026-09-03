"""Tests for confidence scoring utilities."""

from app.models.playbook import ConfidenceTier
from app.utils.confidence import (
    combine_confidence,
    score_from_data_quality,
    score_from_sample_size,
)


def test_score_from_sample_size():
    assert score_from_sample_size(8) == ConfidenceTier.HIGH
    assert score_from_sample_size(4) == ConfidenceTier.MEDIUM
    assert score_from_sample_size(1) == ConfidenceTier.LOW


def test_score_from_data_quality_high():
    tier = score_from_data_quality(
        sample_size=8,
        has_estimates=True,
        has_correlation=True,
        source_count=2,
    )
    assert tier in {ConfidenceTier.HIGH, ConfidenceTier.MEDIUM}


def test_score_from_data_quality_low():
    tier = score_from_data_quality(sample_size=1)
    assert tier == ConfidenceTier.LOW


def test_combine_confidence():
    assert combine_confidence(ConfidenceTier.HIGH, ConfidenceTier.LOW) == ConfidenceTier.LOW
    assert combine_confidence(ConfidenceTier.HIGH, ConfidenceTier.MEDIUM) == ConfidenceTier.MEDIUM
