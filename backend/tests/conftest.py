"""Shared pytest fixtures."""

from datetime import date

import pandas as pd
import pytest
from app.config import Settings
from app.models.analysis import PeerMapResult, ReactionPatternAnalysis
from app.models.playbook import ConfidenceTier, PeerRelationship, ReactionArchetype, ReportOutcome
from app.utils.cache import TTLCache


@pytest.fixture
def settings() -> Settings:
    return Settings(
        finnhub_api_key="test-finnhub-key",
        tavily_api_key="test-tavily-key",
        sec_user_agent="EarningsPulse test@example.com",
    )


@pytest.fixture
def cache() -> TTLCache:
    return TTLCache(default_ttl_seconds=60, max_entries=128)


@pytest.fixture
def sample_price_history() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Open": [100.0, 101.0, 99.0, 103.0, 105.0],
            "High": [102.0, 103.0, 100.0, 106.0, 108.0],
            "Low": [99.0, 100.0, 97.0, 101.0, 104.0],
            "Close": [101.0, 102.0, 98.0, 105.0, 107.0],
            "Volume": [1_000_000, 1_100_000, 1_200_000, 1_300_000, 1_400_000],
        },
        index=pd.to_datetime(
            ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]
        ),
    )


@pytest.fixture
def earnings_date() -> date:
    return date(2024, 1, 3)


@pytest.fixture
def mock_research_bundle():
    return {
        "ticker": "AAPL",
        "company_name": "Apple Inc.",
        "earnings_date": "2025-09-10",
        "is_after_hours": True,
        "last_earnings_summary": "Latest 10-Q filed 2024-08-01",
        "recent_news": [
            {
                "title": "Apple earnings preview",
                "url": "https://example.com/aapl",
                "content": "Analysts expect a beat on services revenue.",
                "score": 0.9,
            }
        ],
        "filing_links": [{"form": "10-Q", "url": "https://sec.gov/aapl", "date": "2024-08-01"}],
        "analyst_context": "Consensus expects modest beat.",
        "sector_context": "Consumer tech demand stable.",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "sources": [
            {"title": "Apple news", "url": "https://example.com/aapl", "source_type": "tavily"}
        ],
    }


@pytest.fixture
def mock_reaction_analysis():
    from app.models.analysis import EarningsReactionEvent

    return ReactionPatternAnalysis(
        ticker="AAPL",
        archetype=ReactionArchetype.DIP_THEN_RALLY,
        archetype_description="Dip-then-rally pattern",
        events_analyzed=2,
        events=[
            EarningsReactionEvent(
                ticker="AAPL",
                earnings_date=date(2024, 5, 2),
                report_outcome=ReportOutcome.BEAT,
                initial_move_pct=-2.0,
                dip_pct=-3.5,
                recovery_pct=5.0,
                pattern=ReactionArchetype.DIP_THEN_RALLY,
            )
        ],
        pattern_counts={"dip_then_rally": 1},
        avg_dip_pct=-3.5,
        avg_recovery_pct=5.0,
        dip_frequency_on_positive=1.0,
        expected_dip_zone={"min": -3.5, "max": -3.5, "median": -3.5},
        confidence=ConfidenceTier.MEDIUM,
    )


@pytest.fixture
def mock_peer_map_result():
    from app.models.analysis import PeerCandidate

    return PeerMapResult(
        reporting_ticker="AAPL",
        sector="Technology",
        industry="Consumer Electronics",
        peers=[
            PeerCandidate(
                ticker="MSFT",
                company_name="Microsoft",
                relationship=PeerRelationship.DIRECT_PEER,
                correlation_score=0.62,
                expected_direction="same",
                rationale="Same cloud_software group",
                earnings_events_used=2,
            )
        ],
        confidence=ConfidenceTier.MEDIUM,
    )
