"""Earnings reaction pattern analysis engine."""

from __future__ import annotations

from datetime import date, timedelta
from statistics import mean, median
from typing import Any

from app.config import Settings, get_settings
from app.models.analysis import EarningsReactionEvent, ReactionPatternAnalysis
from app.models.data import EarningsEvent, OHLCVBar
from app.models.playbook import ConfidenceTier, ReactionArchetype, ReportOutcome
from app.services.earnings_calendar import EarningsCalendarService
from app.services.monte_carlo import simulate_reaction_paths
from app.services.price_data import PriceDataService
from app.services.reaction_chart import build_reaction_chart_data, ensure_chart_history_bars
from app.services.reaction_validation import validate_reaction_patterns
from app.utils.cache import TTLCache, app_cache
from app.utils.confidence import combine_confidence, score_from_data_quality


def _earnings_date(event: EarningsReactionEvent) -> date:
    return event.earnings_date


ARCHETYPE_DESCRIPTIONS: dict[ReactionArchetype, str] = {
    ReactionArchetype.DIP_THEN_RALLY: (
        "Positive reactions often dip first before recovering — watch for reversal entry zones."
    ),
    ReactionArchetype.IMMEDIATE_RIP: (
        "Positive reactions tend to rally immediately with limited initial dip."
    ),
    ReactionArchetype.SELL_THE_NEWS: (
        "Positive reports often fade after an initial pop — "
        "avoid chasing extended after-hours highs."
    ),
    ReactionArchetype.GAP_AND_HOLD: (
        "Negative reactions tend to gap down and stay under pressure."
    ),
    ReactionArchetype.VOLATILITY_PIN: (
        "Reactions are mixed or range-bound — reduce size and wait for clarity."
    ),
    ReactionArchetype.INSUFFICIENT_DATA: (
        "Not enough historical earnings reactions to classify a reliable pattern."
    ),
}

POSITIVE_OUTCOMES = {ReportOutcome.BEAT, ReportOutcome.INLINE}
DIP_THRESHOLD_PCT = -0.5
RALLY_RECOVERY_MIN_PCT = 1.0
IMMEDIATE_RIP_MIN_PCT = 2.0
SELL_THE_NEWS_FADE_PCT = -1.0
GAP_DOWN_THRESHOLD_PCT = -2.0
VOLATILITY_BAND_PCT = 1.5


class ReactionAnalyzer:
    """Analyze historical earnings price reactions and classify patterns."""

    def __init__(
        self,
        price_service: PriceDataService | None = None,
        earnings_service: EarningsCalendarService | None = None,
        cache: TTLCache | None = None,
        settings: Settings | None = None,
    ):
        self._price = price_service or PriceDataService()
        self._earnings = earnings_service or EarningsCalendarService()
        self._cache = cache or app_cache
        self._settings = settings or get_settings()

    async def analyze_ticker(
        self,
        ticker: str,
        *,
        limit: int | None = None,
        window_days: int | None = None,
        use_cache: bool = True,
    ) -> ReactionPatternAnalysis:
        """Fetch historical earnings and analyze reaction patterns for a ticker."""
        normalized = ticker.upper().strip()
        event_limit = limit or self._settings.reaction_history_limit
        window = window_days or self._settings.reaction_window_days
        cache_key = TTLCache.make_key("reaction_analysis", normalized, event_limit, window)
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        historical = await self._earnings.get_historical_earnings(
            normalized,
            limit=event_limit,
            use_cache=use_cache,
        )

        events, all_bars = self._analyze_events_batch(
            normalized,
            historical.events,
            window_days=window,
            use_cache=use_cache,
        )

        options_data = self._price.get_options_implied_move(normalized, use_cache=use_cache)
        result = self.aggregate_events(normalized, events, options_data=options_data)

        result.monte_carlo = simulate_reaction_paths(
            events,
            n_simulations=self._settings.monte_carlo_simulations,
        )
        result.validation = validate_reaction_patterns(
            events,
            train_ratio=self._settings.validation_train_ratio,
        )
        if events:
            first = min(event.earnings_date for event in events)
            last = max(event.earnings_date for event in events)
            result.backtest_years = round((last - first).days / 365.25, 1)
            latest = max(events, key=_earnings_date)
            if latest.baseline_price is not None:
                latest_bars = self._price.slice_window_bars(
                    self._load_bars_for_event(normalized, latest.earnings_date, window, use_cache),
                    latest.earnings_date,
                    window_days=window,
                )
                result.fib_levels = self._price.compute_fib_retracement(
                    latest_bars,
                    latest.earnings_date,
                )

        if all_bars and events:
            chart_bars = ensure_chart_history_bars(
                normalized,
                events,
                all_bars,
                self._price,
                use_cache=use_cache,
            )
            result.reaction_chart = build_reaction_chart_data(
                normalized,
                events,
                chart_bars,
                result,
                window_days=window,
            )

        if result.validation and result.validation.overfitting_risk == "high":
            result.confidence = combine_confidence(result.confidence, ConfidenceTier.LOW)
        elif result.validation and result.validation.overfitting_risk == "medium":
            result.confidence = combine_confidence(result.confidence, ConfidenceTier.MEDIUM)

        if use_cache:
            self._cache.set(cache_key, result, ttl_seconds=3600)

        return result

    def _analyze_events_batch(
        self,
        ticker: str,
        earnings_events: list[EarningsEvent],
        *,
        window_days: int,
        use_cache: bool,
    ) -> tuple[list[EarningsReactionEvent], list[OHLCVBar]]:
        if not earnings_events:
            return [], []

        min_date = min(event.report_date for event in earnings_events) - timedelta(days=window_days)
        max_date = max(event.report_date for event in earnings_events) + timedelta(days=window_days)

        try:
            all_bars = self._price.fetch_ohlcv(ticker, min_date, max_date, use_cache=use_cache)
        except Exception:
            all_bars = []

        events: list[EarningsReactionEvent] = []
        for earnings_event in earnings_events:
            if all_bars:
                window_bars = self._price.slice_window_bars(
                    all_bars,
                    earnings_event.report_date,
                    window_days=window_days,
                )
                analyzed = self.analyze_window(
                    ticker,
                    earnings_event.report_date,
                    window_bars,
                    report_outcome=self._infer_report_outcome(earnings_event),
                    window_days=window_days,
                )
            else:
                analyzed = self.analyze_event(
                    ticker,
                    earnings_event,
                    window_days=window_days,
                    use_cache=use_cache,
                )
            if analyzed is not None:
                events.append(analyzed)
        return events, all_bars

    def _load_bars_for_event(
        self,
        ticker: str,
        earnings_date: date,
        window_days: int,
        use_cache: bool,
    ) -> list[OHLCVBar]:
        try:
            window = self._price.fetch_around_earnings(
                ticker,
                earnings_date,
                window_days=window_days + 20,
                use_cache=use_cache,
            )
            return window.bars
        except Exception:
            return []

    def analyze_event(
        self,
        ticker: str,
        earnings_event: EarningsEvent,
        *,
        window_days: int = 3,
        use_cache: bool = True,
    ) -> EarningsReactionEvent | None:
        """Analyze a single earnings event from calendar data."""
        try:
            window = self._price.fetch_around_earnings(
                ticker,
                earnings_event.report_date,
                window_days=window_days,
                use_cache=use_cache,
            )
        except Exception:
            return None

        outcome = self._infer_report_outcome(earnings_event)
        return self.analyze_window(
            ticker,
            earnings_event.report_date,
            window.bars,
            report_outcome=outcome,
            window_days=window_days,
        )

    def analyze_window(
        self,
        ticker: str,
        earnings_date: date,
        bars: list[OHLCVBar],
        *,
        report_outcome: ReportOutcome | None = None,
        window_days: int = 3,
    ) -> EarningsReactionEvent | None:
        """Analyze price bars around a single earnings date."""
        if len(bars) < 2:
            return None

        metrics = self._price.calculate_dip_recovery(bars, earnings_date)
        baseline = metrics.get("baseline_price")
        dip_pct = metrics.get("dip_pct")
        recovery_pct = metrics.get("recovery_pct")

        initial_move_pct = self._calculate_initial_move(bars, earnings_date, baseline)
        if initial_move_pct is None:
            return None

        outcome = report_outcome or self._outcome_from_move(initial_move_pct)
        time_to_bottom_days = self._time_to_bottom_days(bars, earnings_date, baseline)

        pattern = self.classify_single_reaction(
            outcome=outcome,
            initial_move_pct=initial_move_pct,
            dip_pct=dip_pct,
            recovery_pct=recovery_pct,
        )

        return EarningsReactionEvent(
            ticker=ticker.upper().strip(),
            earnings_date=earnings_date,
            report_outcome=outcome,
            initial_move_pct=round(initial_move_pct, 4),
            dip_pct=dip_pct,
            recovery_pct=recovery_pct,
            time_to_bottom_days=time_to_bottom_days,
            pattern=pattern,
            baseline_price=baseline,
            window_days=window_days,
        )

    @staticmethod
    def classify_single_reaction(
        *,
        outcome: ReportOutcome,
        initial_move_pct: float,
        dip_pct: float | None,
        recovery_pct: float | None,
    ) -> ReactionArchetype:
        """Classify a single earnings reaction into an archetype."""
        if outcome == ReportOutcome.MISS:
            if abs(initial_move_pct) <= VOLATILITY_BAND_PCT:
                return ReactionArchetype.VOLATILITY_PIN
            return ReactionArchetype.GAP_AND_HOLD

        has_dip = dip_pct is not None and dip_pct <= DIP_THRESHOLD_PCT
        has_recovery = recovery_pct is not None and recovery_pct >= RALLY_RECOVERY_MIN_PCT

        if has_dip and has_recovery and recovery_pct > abs(dip_pct or 0):
            return ReactionArchetype.DIP_THEN_RALLY

        if initial_move_pct >= IMMEDIATE_RIP_MIN_PCT and not has_dip:
            return ReactionArchetype.IMMEDIATE_RIP

        if (
            initial_move_pct > 0
            and recovery_pct is not None
            and recovery_pct < initial_move_pct + SELL_THE_NEWS_FADE_PCT
        ):
            return ReactionArchetype.SELL_THE_NEWS

        if abs(initial_move_pct) <= VOLATILITY_BAND_PCT:
            return ReactionArchetype.VOLATILITY_PIN

        if initial_move_pct > 0:
            return ReactionArchetype.IMMEDIATE_RIP

        if outcome == ReportOutcome.INLINE:
            return ReactionArchetype.VOLATILITY_PIN

        return ReactionArchetype.GAP_AND_HOLD

    def aggregate_events(
        self,
        ticker: str,
        events: list[EarningsReactionEvent],
        *,
        options_data: dict[str, Any] | None = None,
    ) -> ReactionPatternAnalysis:
        """Aggregate per-event reactions into a ticker-level pattern analysis."""
        if not events:
            return ReactionPatternAnalysis(
                ticker=ticker.upper().strip(),
                archetype=ReactionArchetype.INSUFFICIENT_DATA,
                archetype_description=ARCHETYPE_DESCRIPTIONS[ReactionArchetype.INSUFFICIENT_DATA],
                events_analyzed=0,
                confidence=ConfidenceTier.LOW,
            )

        pattern_counts: dict[str, int] = {}
        for event in events:
            key = event.pattern.value
            pattern_counts[key] = pattern_counts.get(key, 0) + 1

        archetype = self._select_dominant_archetype(events)
        positive_events = [
            e for e in events if e.report_outcome in POSITIVE_OUTCOMES or e.initial_move_pct > 0
        ]
        dipped_positive = [
            e for e in positive_events if e.dip_pct is not None and e.dip_pct <= DIP_THRESHOLD_PCT
        ]

        dip_values = [e.dip_pct for e in dipped_positive if e.dip_pct is not None]
        recovery_values = [
            e.recovery_pct
            for e in positive_events
            if e.recovery_pct is not None and e.recovery_pct > 0
        ]

        avg_dip = round(mean(dip_values), 4) if dip_values else None
        avg_recovery = round(mean(recovery_values), 4) if recovery_values else None
        dip_frequency = (
            round(len(dipped_positive) / len(positive_events), 4) if positive_events else None
        )

        expected_dip_zone = None
        if dip_values:
            expected_dip_zone = {
                "min": round(min(dip_values), 4),
                "max": round(max(dip_values), 4),
                "median": round(median(dip_values), 4),
            }

        historical_move_pct = round(mean(abs(event.initial_move_pct) for event in events), 2)

        implied_move_pct: float | None = None
        volatility_assessment: str | None = None
        options_summary: str | None = None

        if options_data is not None:
            raw_implied = options_data.get("implied_move_pct")
            if isinstance(raw_implied, int | float) and raw_implied == raw_implied:
                implied_move_pct = float(raw_implied)

        if implied_move_pct is not None and historical_move_pct is not None:
            if implied_move_pct > historical_move_pct * 1.15:
                volatility_assessment = "OVERPRICED"
                options_summary = (
                    f"Options market implies ±{implied_move_pct:.1f}% move vs. "
                    f"±{historical_move_pct:.1f}% historical avg move (volatility overpriced)."
                )
            elif implied_move_pct < historical_move_pct * 0.85:
                volatility_assessment = "UNDERPRICED"
                options_summary = (
                    f"Options market implies ±{implied_move_pct:.1f}% move vs. "
                    f"±{historical_move_pct:.1f}% historical avg move (volatility underpriced)."
                )
            else:
                volatility_assessment = "INLINE"
                options_summary = (
                    f"Options market implies ±{implied_move_pct:.1f}% move, "
                    f"closely aligned with ±{historical_move_pct:.1f}% historical avg move."
                )
        elif implied_move_pct is not None:
            options_summary = (
                f"Options market implies ±{implied_move_pct:.1f}% move for upcoming earnings."
            )
        elif historical_move_pct is not None:
            options_summary = (
                f"Historical average realized move is ±{historical_move_pct:.1f}% "
                "across past earnings."
            )

        has_estimates = any(e.report_outcome is not None for e in events)
        confidence = score_from_data_quality(
            sample_size=len(events),
            has_estimates=has_estimates,
        )

        return ReactionPatternAnalysis(
            ticker=ticker.upper().strip(),
            archetype=archetype,
            archetype_description=ARCHETYPE_DESCRIPTIONS[archetype],
            events_analyzed=len(events),
            events=sorted(events, key=_earnings_date, reverse=True),
            pattern_counts=pattern_counts,
            avg_dip_pct=avg_dip,
            avg_recovery_pct=avg_recovery,
            dip_frequency_on_positive=dip_frequency,
            expected_dip_zone=expected_dip_zone,
            implied_move_pct=implied_move_pct,
            historical_move_pct=historical_move_pct,
            volatility_assessment=volatility_assessment,
            options_summary=options_summary,
            confidence=confidence,
        )

    @staticmethod
    def _select_dominant_archetype(
        events: list[EarningsReactionEvent],
    ) -> ReactionArchetype:
        """Pick dominant archetype with recency weighting."""
        if not events:
            return ReactionArchetype.INSUFFICIENT_DATA

        weighted: dict[str, float] = {}
        for idx, event in enumerate(sorted(events, key=_earnings_date, reverse=True)):
            weight = max(1.0, len(events) - idx)
            key = event.pattern.value
            weighted[key] = weighted.get(key, 0.0) + weight

        dominant_key = max(weighted, key=lambda key: weighted[key])
        return ReactionArchetype(dominant_key)

    @staticmethod
    def _infer_report_outcome(
        earnings_event: EarningsEvent,
    ) -> ReportOutcome | None:
        """Infer beat/miss/inline from EPS data when available."""
        estimate = earnings_event.eps_estimate
        actual = earnings_event.eps_actual
        if estimate is None or actual is None:
            return None

        surprise_pct = ((actual - estimate) / abs(estimate)) * 100 if estimate else 0
        if surprise_pct > 2:
            return ReportOutcome.BEAT
        if surprise_pct < -2:
            return ReportOutcome.MISS
        return ReportOutcome.INLINE

    @staticmethod
    def _outcome_from_move(initial_move_pct: float) -> ReportOutcome:
        if initial_move_pct > 1.0:
            return ReportOutcome.BEAT
        if initial_move_pct < -1.0:
            return ReportOutcome.MISS
        return ReportOutcome.INLINE

    @staticmethod
    def _calculate_initial_move(
        bars: list[OHLCVBar],
        earnings_date: date,
        baseline: float | None,
    ) -> float | None:
        if baseline is None or baseline == 0:
            return None

        ordered = sorted(bars, key=lambda bar: bar.date)
        post = [bar for bar in ordered if bar.date >= earnings_date]
        if not post:
            return None

        first_post_close = post[0].close
        return ((first_post_close - baseline) / baseline) * 100

    @staticmethod
    def _time_to_bottom_days(
        bars: list[OHLCVBar],
        earnings_date: date,
        baseline: float | None,
    ) -> int | None:
        if baseline is None:
            return None

        ordered = sorted(bars, key=lambda bar: bar.date)
        post = [bar for bar in ordered if bar.date >= earnings_date]
        if not post:
            return None

        low_bar = min(post, key=lambda bar: bar.low)
        return (low_bar.date - earnings_date).days
