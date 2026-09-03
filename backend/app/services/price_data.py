"""yfinance wrapper for historical price data."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable

import yfinance as yf

from app.models.data import EarningsWindowPrices, OHLCVBar, PriceReturnMetrics
from app.services.errors import DataNotFoundError, ServiceError
from app.utils.cache import TTLCache, app_cache


class PriceDataService:
    """Fetch and analyze historical OHLCV data."""

    def __init__(self, cache: TTLCache | None = None):
        self._cache = cache or app_cache

    def fetch_ohlcv(
        self,
        ticker: str,
        start: date,
        end: date,
        *,
        use_cache: bool = True,
    ) -> list[OHLCVBar]:
        """Fetch daily OHLCV bars for a ticker in [start, end]."""
        normalized = ticker.upper().strip()
        if end < start:
            raise ValueError("end date must be on or after start date")

        cache_key = TTLCache.make_key("ohlcv", normalized, start, end)
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        try:
            history = yf.Ticker(normalized).history(
                start=start.isoformat(),
                end=(end + timedelta(days=1)).isoformat(),
                auto_adjust=True,
            )
        except Exception as exc:
            raise ServiceError(
                f"Failed to fetch price data for {normalized}: {exc}",
                service="yfinance",
                retryable=True,
            ) from exc

        if history.empty:
            raise DataNotFoundError(
                f"No price data found for {normalized} between {start} and {end}",
                service="yfinance",
            )

        bars = [
            OHLCVBar(
                date=idx.date(),
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                volume=int(row["Volume"]) if row["Volume"] == row["Volume"] else None,
            )
            for idx, row in history.iterrows()
        ]

        if use_cache:
            self._cache.set(cache_key, bars, ttl_seconds=3600)

        return bars

    def fetch_around_earnings(
        self,
        ticker: str,
        earnings_date: date,
        *,
        window_days: int = 3,
        use_cache: bool = True,
    ) -> EarningsWindowPrices:
        """Fetch price bars in a ±window_days range around an earnings date."""
        start = earnings_date - timedelta(days=window_days)
        end = earnings_date + timedelta(days=window_days)
        bars = self.fetch_ohlcv(ticker, start, end, use_cache=use_cache)
        metrics = self.calculate_window_metrics(bars) if bars else None
        return EarningsWindowPrices(
            ticker=ticker.upper().strip(),
            earnings_date=earnings_date,
            window_days=window_days,
            bars=bars,
            metrics=metrics,
        )

    @staticmethod
    def calculate_window_metrics(bars: Iterable[OHLCVBar]) -> PriceReturnMetrics | None:
        """Calculate return, drawdown, and gain metrics for a price window."""
        ordered = sorted(bars, key=lambda bar: bar.date)
        if len(ordered) < 2:
            return None

        start_price = ordered[0].close
        end_price = ordered[-1].close
        high_price = max(bar.high for bar in ordered)
        low_price = min(bar.low for bar in ordered)

        if start_price == 0:
            return None

        total_return_pct = ((end_price - start_price) / start_price) * 100
        max_drawdown_pct = ((low_price - start_price) / start_price) * 100
        max_gain_pct = ((high_price - start_price) / start_price) * 100

        return PriceReturnMetrics(
            start_price=start_price,
            end_price=end_price,
            high_price=high_price,
            low_price=low_price,
            total_return_pct=round(total_return_pct, 4),
            max_drawdown_pct=round(max_drawdown_pct, 4),
            max_gain_pct=round(max_gain_pct, 4),
        )

    def calculate_dip_recovery(
        self,
        bars: list[OHLCVBar],
        earnings_date: date,
    ) -> dict[str, float | None]:
        """
        Calculate dip and recovery metrics relative to earnings date close.

        Uses the last bar on or before earnings_date as baseline.
        """
        ordered = sorted(bars, key=lambda bar: bar.date)
        if not ordered:
            return {
                "baseline_price": None,
                "dip_pct": None,
                "recovery_pct": None,
            }

        baseline_candidates = [bar for bar in ordered if bar.date < earnings_date]
        if not baseline_candidates:
            baseline_candidates = [bar for bar in ordered if bar.date <= earnings_date]
        if not baseline_candidates:
            baseline_candidates = [ordered[0]]

        baseline = baseline_candidates[-1].close
        post_earnings = [bar for bar in ordered if bar.date >= earnings_date]
        if not post_earnings or baseline == 0:
            return {
                "baseline_price": baseline,
                "dip_pct": None,
                "recovery_pct": None,
            }

        lows = [bar.low for bar in post_earnings]
        highs = [bar.high for bar in post_earnings]
        min_low = min(lows)
        max_high = max(highs)

        dip_pct = ((min_low - baseline) / baseline) * 100
        recovery_pct = ((max_high - baseline) / baseline) * 100

        return {
            "baseline_price": baseline,
            "dip_pct": round(dip_pct, 4),
            "recovery_pct": round(recovery_pct, 4),
        }

    @staticmethod
    def get_company_name(ticker: str) -> str | None:
        """Best-effort company name lookup via yfinance metadata."""
        try:
            info = yf.Ticker(ticker.upper().strip()).info
            return info.get("shortName") or info.get("longName")
        except Exception:
            return None
