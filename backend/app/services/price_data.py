"""yfinance wrapper for historical price data."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime, timedelta

import pandas as pd

from app.models.data import EarningsWindowPrices, OHLCVBar, PriceReturnMetrics
from app.services.company_names import get_company_name as lookup_company_name
from app.services.errors import DataNotFoundError, ServiceError
from app.services.yfinance_client import call_with_retry, download, get_ticker
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
            history = call_with_retry(
                f"history:{normalized}",
                lambda: get_ticker(normalized).history(
                    start=start.isoformat(),
                    end=(end + timedelta(days=1)).isoformat(),
                    auto_adjust=True,
                ),
            )
        except Exception as exc:
            raise ServiceError(
                f"Failed to fetch price data for {normalized}: {exc}",
                service="yfinance",
                retryable=True,
            ) from exc

        bars = self._dataframe_to_bars(history, normalized)
        if not bars:
            raise DataNotFoundError(
                f"No price data found for {normalized} between {start} and {end}",
                service="yfinance",
            )

        if use_cache:
            self._cache.set(cache_key, bars, ttl_seconds=3600)

        return bars

    def fetch_ohlcv_many(
        self,
        tickers: list[str],
        start: date,
        end: date,
        *,
        use_cache: bool = True,
    ) -> dict[str, list[OHLCVBar]]:
        """Fetch OHLCV for multiple tickers in one Yahoo request when possible."""
        normalized = [t.upper().strip() for t in tickers if t.strip()]
        if not normalized:
            return {}

        cache_key = TTLCache.make_key("ohlcv_batch", sorted(normalized), start, end)
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        result: dict[str, list[OHLCVBar]] = {t: [] for t in normalized}

        if len(normalized) == 1:
            result[normalized[0]] = self.fetch_ohlcv(normalized[0], start, end, use_cache=use_cache)
            return result

        try:
            frame = call_with_retry(
                f"download:{','.join(normalized)}",
                lambda: download(
                    normalized,
                    start=start.isoformat(),
                    end=(end + timedelta(days=1)).isoformat(),
                ),
            )
        except Exception:
            # Fall back to sequential single-ticker fetches.
            for ticker in normalized:
                try:
                    result[ticker] = self.fetch_ohlcv(ticker, start, end, use_cache=use_cache)
                except Exception:
                    result[ticker] = []
            return result

        if frame.empty:
            return result

        if isinstance(frame.columns, pd.MultiIndex):
            for ticker in normalized:
                if ticker not in frame.columns.get_level_values(1):
                    continue
                ticker_frame = frame.xs(ticker, axis=1, level=1, drop_level=False)
                if isinstance(ticker_frame.columns, pd.MultiIndex):
                    ticker_frame.columns = ticker_frame.columns.droplevel(1)
                result[ticker] = self._dataframe_to_bars(ticker_frame, ticker)
        else:
            result[normalized[0]] = self._dataframe_to_bars(frame, normalized[0])

        if use_cache:
            self._cache.set(cache_key, result, ttl_seconds=3600)

        return result

    @staticmethod
    def _dataframe_to_bars(history: pd.DataFrame, ticker: str) -> list[OHLCVBar]:
        if history is None or history.empty:
            return []

        bars: list[OHLCVBar] = []
        for idx, row in history.iterrows():
            if isinstance(idx, datetime):
                bar_date = idx.date()
            elif isinstance(idx, date):
                bar_date = idx
            else:
                continue
            try:
                bars.append(
                    OHLCVBar(
                        date=bar_date,
                        open=float(row["Open"]),
                        high=float(row["High"]),
                        low=float(row["Low"]),
                        close=float(row["Close"]),
                        volume=(int(row["Volume"]) if row["Volume"] == row["Volume"] else None),
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
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
        """Best-effort company name without Yahoo quoteSummary (.info) calls."""
        return lookup_company_name(ticker)
