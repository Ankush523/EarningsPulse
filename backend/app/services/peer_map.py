"""Peer spillover mapping with static taxonomy and dynamic correlation."""

from __future__ import annotations

from datetime import date, timedelta
from statistics import mean

from app.models.analysis import PeerCandidate, PeerMapResult
from app.models.data import OHLCVBar
from app.models.playbook import ConfidenceTier, PeerRelationship
from app.services.earnings_calendar import EarningsCalendarService
from app.services.price_data import PriceDataService
from app.utils.cache import TTLCache, app_cache
from app.utils.confidence import score_from_data_quality

# GICS-inspired peer groups for major sectors/themes.
# Keys are canonical group names; values are ticker lists.
SECTOR_PEER_GROUPS: dict[str, list[str]] = {
    "semiconductors": [
        "NVDA",
        "AMD",
        "INTC",
        "AVGO",
        "MRVL",
        "MU",
        "QCOM",
        "TXN",
        "ASML",
        "ARM",
        "LRCX",
        "KLAC",
        "AMAT",
        "ON",
        "MCHP",
    ],
    "storage": ["WDC", "STX", "MU", "NTAP", "PSTG"],
    "cloud_software": [
        "MSFT",
        "AMZN",
        "GOOGL",
        "META",
        "CRM",
        "ORCL",
        "SNOW",
        "DDOG",
        "NET",
    ],
    "enterprise_software": [
        "MSFT",
        "ORCL",
        "CRM",
        "ADBE",
        "NOW",
        "INTU",
        "PANW",
        "CRWD",
    ],
    "consumer_tech": ["AAPL", "SSNLF", "SONY", "QCOM", "SWKS"],
    "financials": ["JPM", "BAC", "WFC", "C", "GS", "MS", "BLK", "SCHW"],
    "payments": ["V", "MA", "PYPL", "SQ", "AXP", "FI"],
    "retail_ecommerce": ["AMZN", "WMT", "COST", "TGT", "SHOP", "EBAY", "ETSY"],
    "automotive_ev": ["TSLA", "F", "GM", "RIVN", "LCID", "NIO", "LI"],
    "ai_infrastructure": [
        "NVDA",
        "AMD",
        "SMCI",
        "DELL",
        "HPE",
        "ANET",
        "MRVL",
        "AVGO",
    ],
    "networking": ["CSCO", "ANET", "JNPR", "FFIV", "MSFT", "AMZN"],
    "healthcare_pharma": ["JNJ", "PFE", "MRK", "ABBV", "LLY", "BMY", "AMGN"],
    "energy": ["XOM", "CVX", "COP", "SLB", "EOG", "OXY"],
    "industrial": ["CAT", "DE", "HON", "GE", "MMM", "UPS", "FDX"],
}

# Explicit supply-chain / thematic links beyond sector groups.
THEMATIC_LINKS: dict[str, list[tuple[str, PeerRelationship, str]]] = {
    "NVDA": [
        ("AMD", PeerRelationship.DIRECT_PEER, "GPU/AI accelerator peer"),
        ("MRVL", PeerRelationship.THEMATIC, "AI networking & custom silicon"),
        ("MU", PeerRelationship.SUPPLIER, "HBM/memory supply chain"),
        ("TSM", PeerRelationship.SUPPLIER, "Foundry manufacturing"),
        ("AVGO", PeerRelationship.THEMATIC, "AI infrastructure semis"),
        ("SMCI", PeerRelationship.CUSTOMER, "AI server ecosystem"),
    ],
    "AAPL": [
        ("QCOM", PeerRelationship.SUPPLIER, "Mobile modem/components"),
        ("TSM", PeerRelationship.SUPPLIER, "Chip manufacturing"),
        ("SWKS", PeerRelationship.SUPPLIER, "RF components"),
        ("SSNLF", PeerRelationship.DIRECT_PEER, "Consumer devices peer"),
    ],
    "AMZN": [
        ("MSFT", PeerRelationship.DIRECT_PEER, "Cloud (AWS vs Azure)"),
        ("GOOGL", PeerRelationship.DIRECT_PEER, "Cloud (AWS vs GCP)"),
        ("WMT", PeerRelationship.DIRECT_PEER, "Retail/e-commerce"),
        ("SHOP", PeerRelationship.THEMATIC, "E-commerce ecosystem"),
    ],
    "TSLA": [
        ("F", PeerRelationship.DIRECT_PEER, "Legacy auto peer"),
        ("GM", PeerRelationship.DIRECT_PEER, "Legacy auto peer"),
        ("RIVN", PeerRelationship.DIRECT_PEER, "EV peer"),
        ("NVDA", PeerRelationship.SUPPLIER, "Autonomy/AI chips"),
    ],
    "MRVL": [
        ("NVDA", PeerRelationship.THEMATIC, "AI/data center networking"),
        ("AVGO", PeerRelationship.DIRECT_PEER, "Networking/custom silicon"),
        ("AMD", PeerRelationship.DIRECT_PEER, "Data center semis"),
    ],
    "JPM": [
        ("BAC", PeerRelationship.DIRECT_PEER, "Money center bank peer"),
        ("WFC", PeerRelationship.DIRECT_PEER, "Money center bank peer"),
        ("GS", PeerRelationship.DIRECT_PEER, "Investment banking peer"),
        ("V", PeerRelationship.THEMATIC, "Payments ecosystem"),
    ],
}


def find_groups_for_ticker(ticker: str) -> list[str]:
    """Return sector group names that include the ticker."""
    normalized = ticker.upper().strip()
    return [group for group, members in SECTOR_PEER_GROUPS.items() if normalized in members]


def get_static_peers(ticker: str) -> list[tuple[str, PeerRelationship, str, str | None]]:
    """
    Return static peer candidates for a ticker.

    Each tuple: (peer_ticker, relationship, rationale, sector_group)
    """
    normalized = ticker.upper().strip()
    peers: dict[str, tuple[PeerRelationship, str, str | None]] = {}

    for group_name in find_groups_for_ticker(normalized):
        for member in SECTOR_PEER_GROUPS[group_name]:
            if member == normalized:
                continue
            peers.setdefault(
                member,
                (PeerRelationship.DIRECT_PEER, f"Same {group_name} group", group_name),
            )

    for peer, relationship, rationale in THEMATIC_LINKS.get(normalized, []):
        peers[peer] = (relationship, rationale, "thematic")

    return [
        (peer, relationship, rationale, sector)
        for peer, (relationship, rationale, sector) in peers.items()
    ]


CORRELATION_WINDOW_DAYS = 3
MIN_CORRELATION_EVENTS = 2


class PeerMapService:
    """Build ranked peer spillover maps for a reporting ticker."""

    def __init__(
        self,
        price_service: PriceDataService | None = None,
        earnings_service: EarningsCalendarService | None = None,
        cache: TTLCache | None = None,
    ):
        self._price = price_service or PriceDataService()
        self._earnings = earnings_service or EarningsCalendarService()
        self._cache = cache or app_cache

    async def build_peer_map(
        self,
        ticker: str,
        *,
        max_peers: int = 10,
        earnings_limit: int = 6,
        use_cache: bool = True,
    ) -> PeerMapResult:
        """Build a ranked peer map for the reporting ticker."""
        normalized = ticker.upper().strip()
        cache_key = TTLCache.make_key("peer_map", normalized, max_peers, earnings_limit)
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        groups = find_groups_for_ticker(normalized)
        sector = groups[0] if groups else None
        industry = groups[-1] if groups else None
        static_peers = get_static_peers(normalized)

        # Dynamic peer discovery via Finnhub
        dynamic_peers: list[tuple[str, PeerRelationship, str, str | None]] = []
        try:
            finnhub_peers = await self._earnings.get_peers(normalized, use_cache=use_cache)
            known_tickers = {p for p, _, _, _ in static_peers} | {normalized}
            for fp in finnhub_peers:
                if fp not in known_tickers:
                    dynamic_peers.append(
                        (
                            fp,
                            PeerRelationship.DIRECT_PEER,
                            "Identified via Finnhub market peer graph",
                            sector,
                        )
                    )
                    known_tickers.add(fp)
        except Exception:
            pass

        all_candidate_peers = static_peers + dynamic_peers

        historical = await self._earnings.get_historical_earnings(
            normalized,
            limit=earnings_limit,
            use_cache=use_cache,
        )
        earnings_dates = [
            event.report_date for event in historical.events if event.report_date <= date.today()
        ]

        peer_tickers = [peer for peer, _, _, _ in all_candidate_peers]
        bars_by_ticker = self._load_correlation_bars(
            normalized,
            peer_tickers,
            earnings_dates,
            use_cache=use_cache,
        )

        candidates: list[PeerCandidate] = []
        for peer, relationship, rationale, group in all_candidate_peers:
            correlation = self._compute_earnings_correlation(
                normalized,
                peer,
                earnings_dates,
                bars_by_ticker,
            )
            candidates.append(
                PeerCandidate(
                    ticker=peer,
                    company_name=self._price.get_company_name(peer),
                    relationship=relationship,
                    sector=group or sector,
                    correlation_score=correlation["score"],
                    expected_direction=correlation["direction"],
                    avg_co_move_pct=correlation["avg_co_move_pct"],
                    earnings_events_used=correlation["events_used"],
                    rationale=rationale,
                )
            )

        candidates.sort(
            key=lambda c: (abs(c.correlation_score), c.earnings_events_used),
            reverse=True,
        )
        peers = candidates[:max_peers]

        confidence = score_from_data_quality(
            sample_size=len(peers),
            has_correlation=any(p.earnings_events_used >= MIN_CORRELATION_EVENTS for p in peers),
        )

        result = PeerMapResult(
            reporting_ticker=normalized,
            sector=sector,
            industry=industry,
            peers=peers,
            confidence=confidence if peers else ConfidenceTier.LOW,
        )

        if use_cache:
            self._cache.set(cache_key, result, ttl_seconds=3600)

        return result

    def _load_correlation_bars(
        self,
        reporting_ticker: str,
        peer_tickers: list[str],
        earnings_dates: list[date],
        *,
        use_cache: bool = True,
    ) -> dict[str, list[OHLCVBar]]:
        """Fetch one OHLCV window per ticker covering all earnings dates."""
        if not earnings_dates:
            return {reporting_ticker: [], **{t: [] for t in peer_tickers}}

        start = min(earnings_dates) - timedelta(days=5)
        end = max(earnings_dates) + timedelta(days=CORRELATION_WINDOW_DAYS + 1)
        tickers = [reporting_ticker, *peer_tickers]
        return self._price.fetch_ohlcv_many(tickers, start, end, use_cache=use_cache)

    def _compute_earnings_correlation(
        self,
        reporting_ticker: str,
        peer_ticker: str,
        earnings_dates: list[date],
        bars_by_ticker: dict[str, list[OHLCVBar]],
    ) -> dict:
        """Compute return correlation around reporting ticker earnings dates."""
        if not earnings_dates:
            return {
                "score": 0.0,
                "direction": "weak",
                "avg_co_move_pct": None,
                "events_used": 0,
            }

        reporting_returns: list[float] = []
        peer_returns: list[float] = []
        reporting_bars = bars_by_ticker.get(reporting_ticker, [])
        peer_bars = bars_by_ticker.get(peer_ticker, [])

        for earnings_date in earnings_dates:
            reporting_return = self._earnings_window_return(reporting_bars, earnings_date)
            peer_return = self._earnings_window_return(peer_bars, earnings_date)
            if reporting_return is None or peer_return is None:
                continue
            reporting_returns.append(reporting_return)
            peer_returns.append(peer_return)

        events_used = len(reporting_returns)
        if events_used < MIN_CORRELATION_EVENTS:
            score = self._fallback_correlation_score(reporting_ticker, peer_ticker)
            return {
                "score": score,
                "direction": self._direction_from_score(score),
                "avg_co_move_pct": round(mean(peer_returns), 4) if peer_returns else None,
                "events_used": events_used,
            }

        score = self._pearson_correlation(reporting_returns, peer_returns)
        return {
            "score": round(score, 4),
            "direction": self._direction_from_score(score),
            "avg_co_move_pct": round(mean(peer_returns), 4),
            "events_used": events_used,
        }

    @staticmethod
    def _earnings_window_return(bars: list[OHLCVBar], earnings_date: date) -> float | None:
        ordered = sorted(bars, key=lambda bar: bar.date)
        pre = [bar for bar in ordered if bar.date < earnings_date]
        post = [bar for bar in ordered if bar.date >= earnings_date]
        if not pre or not post:
            return None

        baseline = pre[-1].close
        if baseline == 0:
            return None

        end_close = post[-1].close
        return ((end_close - baseline) / baseline) * 100

    @staticmethod
    def _pearson_correlation(x: list[float], y: list[float]) -> float:
        if len(x) != len(y) or len(x) < 2:
            return 0.0

        mean_x = mean(x)
        mean_y = mean(y)
        num = sum((a - mean_x) * (b - mean_y) for a, b in zip(x, y, strict=True))
        den_x = sum((a - mean_x) ** 2 for a in x) ** 0.5
        den_y = sum((b - mean_y) ** 2 for b in y) ** 0.5
        if den_x == 0 or den_y == 0:
            return 0.0
        return max(-1.0, min(1.0, num / (den_x * den_y)))

    @staticmethod
    def _direction_from_score(score: float) -> str:
        if score >= 0.35:
            return "same"
        if score <= -0.35:
            return "inverse"
        return "weak"

    @staticmethod
    def _fallback_correlation_score(reporting_ticker: str, peer_ticker: str) -> float:
        """Static fallback when insufficient earnings overlap data exists."""
        static = get_static_peers(reporting_ticker)
        for peer, relationship, _, _ in static:
            if peer == peer_ticker:
                if relationship == PeerRelationship.DIRECT_PEER:
                    return 0.55
                if relationship in {
                    PeerRelationship.SUPPLIER,
                    PeerRelationship.CUSTOMER,
                }:
                    return 0.4
                return 0.3
        return 0.15
