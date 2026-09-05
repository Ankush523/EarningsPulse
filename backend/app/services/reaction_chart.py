"""Build reaction workspace chart payloads for the playbook UI."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from statistics import median

from app.models.analysis import EarningsReactionEvent, ReactionPatternAnalysis
from app.models.data import OHLCVBar
from app.models.playbook import (
    ReactionChartData,
    ReactionEventPath,
    ReactionPathPoint,
    ReactionReferenceLine,
)
from app.services.price_data import PriceDataService

CANDLE_LOOKBACK_DAYS = 45
CANDLE_FORWARD_DAYS = 5


def build_reaction_chart_data(
    ticker: str,
    events: list[EarningsReactionEvent],
    all_bars: list[OHLCVBar],
    analysis: ReactionPatternAnalysis,
    *,
    window_days: int,
) -> ReactionChartData | None:
    """Assemble candles, historical paths, median path, and reference lines."""
    if not events or not all_bars:
        return None

    ordered_events = sorted(events, key=lambda event: event.earnings_date)
    focus = ordered_events[-1]
    focus_bars = PriceDataService.slice_chart_bars(
        all_bars,
        focus.earnings_date,
        lookback_days=CANDLE_LOOKBACK_DAYS,
        forward_days=max(window_days, CANDLE_FORWARD_DAYS),
    )
    if len(focus_bars) < 5:
        focus_bars = PriceDataService.slice_window_bars(
            all_bars,
            focus.earnings_date,
            window_days=window_days,
        )
    if len(focus_bars) < 2:
        return None

    baseline = _baseline_price(focus_bars, focus.earnings_date) or focus.baseline_price
    if baseline is None or baseline <= 0:
        return None

    paths: list[ReactionEventPath] = []
    for event in ordered_events[-8:]:
        window_bars = PriceDataService.slice_window_bars(
            all_bars,
            event.earnings_date,
            window_days=window_days,
        )
        event_baseline = _baseline_price(window_bars, event.earnings_date) or event.baseline_price
        if event_baseline is None or event_baseline <= 0:
            continue
        points = _path_points(window_bars, event.earnings_date, event_baseline)
        if len(points) < 2:
            continue
        paths.append(
            ReactionEventPath(
                earnings_date=event.earnings_date,
                report_outcome=event.report_outcome,
                baseline_price=round(event_baseline, 4),
                points=points,
            )
        )

    if not paths:
        return None

    median_path = _median_path(paths)
    reference_lines = _trading_reference_lines(
        all_bars,
        focus.earnings_date,
        baseline,
        analysis,
    )

    return ReactionChartData(
        ticker=ticker.upper().strip(),
        focus_earnings_date=focus.earnings_date,
        baseline_price=round(baseline, 4),
        window_days=window_days,
        candles=focus_bars,
        paths=paths,
        median_path=median_path,
        reference_lines=reference_lines,
    )


def ensure_chart_history_bars(
    ticker: str,
    events: list[EarningsReactionEvent],
    all_bars: list[OHLCVBar],
    price_service: PriceDataService,
    *,
    use_cache: bool,
) -> list[OHLCVBar]:
    """Extend OHLCV history when the batch fetch does not cover the chart lookback."""
    if not events or not all_bars:
        return all_bars

    focus_date = max(event.earnings_date for event in events)
    chart_start = focus_date - timedelta(days=CANDLE_LOOKBACK_DAYS + 5)
    earliest = min(bar.date for bar in all_bars)
    if earliest <= chart_start:
        return all_bars

    try:
        extra = price_service.fetch_ohlcv(
            ticker,
            chart_start,
            earliest - timedelta(days=1),
            use_cache=use_cache,
        )
    except Exception:
        return all_bars

    merged = {bar.date: bar for bar in all_bars}
    for bar in extra:
        merged[bar.date] = bar
    return sorted(merged.values(), key=lambda bar: bar.date)


def _baseline_price(bars: list[OHLCVBar], earnings_date: date) -> float | None:
    pre = sorted((bar for bar in bars if bar.date < earnings_date), key=lambda bar: bar.date)
    if pre:
        return pre[-1].close
    ordered = sorted(bars, key=lambda bar: bar.date)
    return ordered[0].close if ordered else None


def _path_points(
    bars: list[OHLCVBar],
    earnings_date: date,
    baseline: float,
) -> list[ReactionPathPoint]:
    points: list[ReactionPathPoint] = []
    for bar in sorted(bars, key=lambda item: item.date):
        offset_days = (bar.date - earnings_date).days
        pct = ((bar.close - baseline) / baseline) * 100
        points.append(
            ReactionPathPoint(
                offset_days=offset_days,
                date=bar.date,
                pct_from_baseline=round(pct, 4),
                close=round(bar.close, 4),
            )
        )
    return points


def _median_path(paths: list[ReactionEventPath]) -> list[ReactionPathPoint]:
    by_offset: dict[int, list[float]] = defaultdict(list)
    baseline_samples: dict[int, list[float]] = defaultdict(list)
    date_samples: dict[int, date] = {}

    for path in paths:
        for point in path.points:
            by_offset[point.offset_days].append(point.pct_from_baseline)
            baseline_samples[point.offset_days].append(point.close)
            date_samples[point.offset_days] = point.date

    if not by_offset:
        return []

    median_points: list[ReactionPathPoint] = []
    for offset_days in sorted(by_offset):
        pct_values = by_offset[offset_days]
        close_values = baseline_samples[offset_days]
        median_points.append(
            ReactionPathPoint(
                offset_days=offset_days,
                date=date_samples[offset_days],
                pct_from_baseline=round(median(pct_values), 4),
                close=round(median(close_values), 4),
            )
        )
    return median_points


def _trading_reference_lines(
    bars: list[OHLCVBar],
    earnings_date: date,
    baseline: float,
    analysis: ReactionPatternAnalysis,
) -> list[ReactionReferenceLine]:
    """Pivot, S/R, entry, take-profit, and stop-loss overlays for the chart."""
    lines: list[ReactionReferenceLine] = []
    ordered = sorted(bars, key=lambda bar: bar.date)
    pre = [bar for bar in ordered if bar.date < earnings_date]

    pivot_levels: dict[str, float] = {}
    if pre:
        pivot_levels = PriceDataService.compute_floor_pivot(pre[-1])

    swing = PriceDataService.compute_swing_levels(ordered, earnings_date)

    support_price = pivot_levels.get("support") or swing.get("swing_low")
    resistance_price = pivot_levels.get("resistance") or swing.get("swing_high")
    pivot_price = pivot_levels.get("pivot")

    entry = round(baseline, 4)
    tp, sl = _entry_targets(baseline, analysis, pivot_levels)

    if pivot_price is not None:
        lines.append(ReactionReferenceLine(label="Pivot", price=pivot_price, kind="pivot"))
    if support_price is not None:
        lines.append(ReactionReferenceLine(label="Support", price=support_price, kind="support"))
    if resistance_price is not None:
        lines.append(
            ReactionReferenceLine(label="Resistance", price=resistance_price, kind="resistance")
        )

    lines.append(ReactionReferenceLine(label="Entry", price=entry, kind="entry"))
    if tp is not None:
        lines.append(ReactionReferenceLine(label="TP", price=round(tp, 4), kind="tp"))
    if sl is not None:
        lines.append(ReactionReferenceLine(label="SL", price=round(sl, 4), kind="sl"))

    return lines


def _entry_targets(
    baseline: float,
    analysis: ReactionPatternAnalysis,
    pivot_levels: dict[str, float],
) -> tuple[float | None, float | None]:
    implied = analysis.implied_move_pct
    recovery = analysis.avg_recovery_pct
    dip = analysis.avg_dip_pct

    tp: float | None = None
    sl: float | None = None

    if implied is not None and implied > 0:
        tp = baseline * (1 + implied / 100)
        sl = baseline * (1 - implied / 100)
    elif recovery is not None and dip is not None:
        tp = baseline * (1 + recovery / 100)
        sl = baseline * (1 + dip / 100)

    if tp is None:
        tp = pivot_levels.get("resistance") or pivot_levels.get("resistance_2")
    if sl is None:
        sl = pivot_levels.get("support") or pivot_levels.get("support_2")

    return tp, sl
