"""yfinance wrapper for historical price data."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime, timedelta
from typing import Any

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
    def compute_fib_retracement(
        bars: list[OHLCVBar],
        earnings_date: date,
        *,
        lookback_bars: int = 20,
    ) -> dict[str, float]:
        """
        Fibonacci retracement levels from the pre-earnings swing range.

        Returns price levels and retracement percentages relative to baseline.
        """
        ordered = sorted(bars, key=lambda bar: bar.date)
        pre = [bar for bar in ordered if bar.date < earnings_date]
        if len(pre) < 2:
            return {}

        window = pre[-lookback_bars:]
        swing_high = max(bar.high for bar in window)
        swing_low = min(bar.low for bar in window)
        diff = swing_high - swing_low
        if diff <= 0:
            return {}

        baseline_candidates = pre
        baseline = baseline_candidates[-1].close
        if baseline <= 0:
            return {}

        levels: dict[str, float] = {
            "swing_high": round(swing_high, 4),
            "swing_low": round(swing_low, 4),
            "baseline": round(baseline, 4),
        }
        for ratio, key in (
            (0.236, "fib_0.236"),
            (0.382, "fib_0.382"),
            (0.500, "fib_0.500"),
            (0.618, "fib_0.618"),
        ):
            price = swing_high - ratio * diff
            levels[key] = round(price, 4)
            levels[f"{key}_pct"] = round(((price - baseline) / baseline) * 100, 4)

        return levels

    @staticmethod
    def slice_window_bars(
        bars: list[OHLCVBar],
        earnings_date: date,
        *,
        window_days: int = 3,
    ) -> list[OHLCVBar]:
        """Extract ±window_days bars around an earnings date from a longer series."""
        start = earnings_date - timedelta(days=window_days)
        end = earnings_date + timedelta(days=window_days)
        return [bar for bar in bars if start <= bar.date <= end]

    @staticmethod
    def slice_chart_bars(
        bars: list[OHLCVBar],
        focus_date: date,
        *,
        lookback_days: int = 45,
        forward_days: int = 5,
    ) -> list[OHLCVBar]:
        """Extract daily bars for the reaction chart (history before + days after focus)."""
        start = focus_date - timedelta(days=lookback_days)
        end = focus_date + timedelta(days=forward_days)
        return sorted(
            (bar for bar in bars if start <= bar.date <= end),
            key=lambda bar: bar.date,
        )

    @staticmethod
    def compute_floor_pivot(prev_bar: OHLCVBar) -> dict[str, float]:
        """Classic floor pivot levels from the prior session OHLC."""
        high = prev_bar.high
        low = prev_bar.low
        close = prev_bar.close
        pivot = (high + low + close) / 3
        range_size = high - low
        return {
            "pivot": round(pivot, 4),
            "resistance": round(2 * pivot - low, 4),
            "support": round(2 * pivot - high, 4),
            "resistance_2": round(pivot + range_size, 4),
            "support_2": round(pivot - range_size, 4),
        }

    @staticmethod
    def compute_swing_levels(
        bars: list[OHLCVBar],
        before: date,
        *,
        lookback_bars: int = 20,
    ) -> dict[str, float]:
        """Swing high/low support and resistance from pre-focus bars."""
        pre = sorted((bar for bar in bars if bar.date < before), key=lambda bar: bar.date)
        window = pre[-lookback_bars:]
        if len(window) < 2:
            return {}
        return {
            "swing_high": round(max(bar.high for bar in window), 4),
            "swing_low": round(min(bar.low for bar in window), 4),
        }

    @staticmethod
    def get_company_name(ticker: str) -> str | None:
        """Best-effort company name without Yahoo quoteSummary (.info) calls."""
        return lookup_company_name(ticker)

    def get_options_implied_move(
        self,
        ticker: str,
        target_date: date | None = None,
        *,
        use_cache: bool = True,
    ) -> dict[str, Any] | None:
        """
        Estimate options-implied move % from the ATM straddle.

        Uses the nearest expiration on or after target_date (or the closest upcoming expiration).
        Formula: (ATM Call + ATM Put) / Underlying Price * 0.85 * 100.
        """
        normalized = ticker.upper().strip()
        cache_key = TTLCache.make_key("implied_move", normalized, target_date)
        if use_cache:
            cached = self._cache.get(cache_key)
            if isinstance(cached, dict):
                return cached

        try:
            t = get_ticker(normalized)
            expirations = getattr(t, "options", None)
            if not expirations:
                return None

            selected_exp = expirations[0]
            if target_date:
                target_str = target_date.isoformat()
                future_exps = [e for e in expirations if e >= target_str]
                if future_exps:
                    selected_exp = future_exps[0]

            chain = call_with_retry(
                f"option_chain:{normalized}:{selected_exp}",
                lambda: t.option_chain(selected_exp),
            )
            calls = getattr(chain, "calls", None)
            puts = getattr(chain, "puts", None)

            if calls is None or puts is None or calls.empty or puts.empty:
                return None

            underlying_price = None
            fast_info = getattr(t, "fast_info", None)
            if fast_info:
                underlying_price = getattr(fast_info, "last_price", None) or getattr(
                    fast_info, "previous_close", None
                )

            if not underlying_price:
                try:
                    recent = self.fetch_ohlcv(
                        normalized,
                        date.today() - timedelta(days=7),
                        date.today(),
                        use_cache=use_cache,
                    )
                    if recent:
                        underlying_price = recent[-1].close
                except Exception:
                    pass

            if not underlying_price or underlying_price <= 0:
                return None

            calls_copy = calls.copy()
            puts_copy = puts.copy()

            calls_copy["strike_diff"] = (calls_copy["strike"] - underlying_price).abs()
            atm_call = calls_copy.loc[calls_copy["strike_diff"].idxmin()]

            puts_copy["strike_diff"] = (puts_copy["strike"] - underlying_price).abs()
            atm_put = puts_copy.loc[puts_copy["strike_diff"].idxmin()]

            def extract_price(row: Any) -> float:
                bid = float(row.get("bid", 0) or 0)
                ask = float(row.get("ask", 0) or 0)
                if bid > 0 and ask > 0:
                    return (bid + ask) / 2.0
                return float(row.get("lastPrice", 0) or 0)

            call_price = extract_price(atm_call)
            put_price = extract_price(atm_put)
            straddle_price = call_price + put_price

            if straddle_price <= 0:
                return None

            implied_move_pct = round((straddle_price / underlying_price) * 0.85 * 100, 2)

            result = {
                "ticker": normalized,
                "expiration_date": selected_exp,
                "atm_strike": float(atm_call["strike"]),
                "underlying_price": round(float(underlying_price), 2),
                "straddle_price": round(float(straddle_price), 2),
                "implied_move_pct": implied_move_pct,
            }

            if use_cache:
                self._cache.set(cache_key, result, ttl_seconds=1800)

            return result
        except Exception:
            return None
