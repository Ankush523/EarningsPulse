"""Finnhub wrapper for earnings calendar data with yfinance fallback."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import httpx

from app.config import Settings, get_settings
from app.models.data import (
    EarningsCalendarResponse,
    EarningsEvent,
    HistoricalEarningsResponse,
)
from app.services.errors import ConfigurationError, DataNotFoundError, ServiceError
from app.services.yfinance_client import call_with_retry, get_ticker
from app.utils.cache import TTLCache, app_cache

FINNHUB_BASE_URL = "https://finnhub.io/api/v1"


def _report_date(event: EarningsEvent) -> date:
    return event.report_date


class EarningsCalendarService:
    """Fetch upcoming and historical earnings events."""

    def __init__(
        self,
        settings: Settings | None = None,
        cache: TTLCache | None = None,
        client: httpx.AsyncClient | None = None,
    ):
        self._settings = settings or get_settings()
        self._cache = cache or app_cache
        self._client = client

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is not None:
            return self._client
        return httpx.AsyncClient(timeout=30.0)

    def _require_finnhub_key(self) -> str:
        if not self._settings.finnhub_api_key:
            raise ConfigurationError(
                "FINNHUB_API_KEY is not configured",
                service="finnhub",
            )
        return self._settings.finnhub_api_key

    async def get_upcoming_earnings(
        self,
        *,
        days: int = 7,
        use_cache: bool = True,
    ) -> EarningsCalendarResponse:
        """Fetch earnings events for the next N days."""
        today = date.today()
        to_date = today + timedelta(days=days)
        cache_key = TTLCache.make_key("upcoming_earnings", today, to_date)

        if use_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        api_key = self._require_finnhub_key()
        owns_client = self._client is None
        client = await self._get_client()

        try:
            response = await client.get(
                f"{FINNHUB_BASE_URL}/calendar/earnings",
                params={
                    "from": today.isoformat(),
                    "to": to_date.isoformat(),
                    "token": api_key,
                },
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPStatusError as exc:
            raise ServiceError(
                f"Finnhub calendar request failed: {exc.response.text}",
                service="finnhub",
                retryable=exc.response.status_code >= 500,
            ) from exc
        except httpx.HTTPError as exc:
            raise ServiceError(
                f"Finnhub calendar request failed: {exc}",
                service="finnhub",
                retryable=True,
            ) from exc
        finally:
            if owns_client:
                await client.aclose()

        events: list[EarningsEvent] = [
            self._parse_calendar_event(item)
            for item in payload.get("earningsCalendar", [])
            if item.get("symbol")
        ]

        result = EarningsCalendarResponse(
            from_date=today,
            to_date=to_date,
            events=sorted(events, key=_report_date),
        )

        if use_cache:
            self._cache.set(cache_key, result, ttl_seconds=1800)

        return result

    async def get_historical_earnings(
        self,
        ticker: str,
        *,
        limit: int = 8,
        use_cache: bool = True,
    ) -> HistoricalEarningsResponse:
        """Fetch historical earnings dates for a ticker (last N events)."""
        normalized = ticker.upper().strip()
        cache_key = TTLCache.make_key("historical_earnings", normalized, limit)

        if use_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        # Prefer yfinance — Finnhub `period` is fiscal quarter-end, not report date.
        try:
            result = self._fetch_historical_from_yfinance(normalized, limit)
            if use_cache:
                self._cache.set(cache_key, result, ttl_seconds=3600)
            return result
        except (ServiceError, DataNotFoundError):
            pass

        if self._settings.finnhub_api_key:
            try:
                result = await self._fetch_historical_from_finnhub(normalized, limit)
                past_events = [
                    event for event in result.events if event.report_date <= date.today()
                ]
                if past_events:
                    result = HistoricalEarningsResponse(
                        ticker=normalized,
                        events=past_events[:limit],
                        source=result.source,
                    )
                    if use_cache:
                        self._cache.set(cache_key, result, ttl_seconds=3600)
                    return result
            except (ServiceError, DataNotFoundError):
                pass

        raise DataNotFoundError(
            f"No historical earnings found for {normalized}",
            service="earnings_calendar",
        )

    async def get_next_earnings_date(self, ticker: str) -> date | None:
        """Return the next scheduled earnings date for a ticker, if known."""
        normalized = ticker.upper().strip()

        if self._settings.finnhub_api_key:
            try:
                upcoming = await self.get_upcoming_earnings(days=30, use_cache=True)
                ticker_events = [
                    event for event in upcoming.events if event.ticker.upper() == normalized
                ]
                if ticker_events:
                    return min(event.report_date for event in ticker_events)
            except (ConfigurationError, ServiceError):
                pass

        return self._get_next_earnings_from_yfinance(normalized)

    async def _fetch_historical_from_finnhub(
        self,
        ticker: str,
        limit: int,
    ) -> HistoricalEarningsResponse:
        api_key = self._require_finnhub_key()
        owns_client = self._client is None
        client = await self._get_client()

        try:
            response = await client.get(
                f"{FINNHUB_BASE_URL}/stock/earnings",
                params={"symbol": ticker, "token": api_key},
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPStatusError as exc:
            raise ServiceError(
                f"Finnhub earnings request failed: {exc.response.text}",
                service="finnhub",
                retryable=exc.response.status_code >= 500,
            ) from exc
        except httpx.HTTPError as exc:
            raise ServiceError(
                f"Finnhub earnings request failed: {exc}",
                service="finnhub",
                retryable=True,
            ) from exc
        finally:
            if owns_client:
                await client.aclose()

        if not payload:
            raise DataNotFoundError(
                f"No historical earnings found for {ticker} via Finnhub",
                service="finnhub",
            )

        events: list[EarningsEvent] = []
        for item in payload[:limit]:
            period = item.get("period")
            report_date = self._parse_period(period) if period else None
            if report_date is None:
                continue
            events.append(
                EarningsEvent(
                    ticker=ticker,
                    report_date=report_date,
                    report_time=None,
                    eps_estimate=item.get("estimate"),
                    eps_actual=item.get("actual"),
                    quarter=self._extract_quarter(period),
                    year=self._extract_year(period),
                )
            )

        if not events:
            raise DataNotFoundError(
                f"No parseable historical earnings for {ticker} via Finnhub",
                service="finnhub",
            )

        return HistoricalEarningsResponse(
            ticker=ticker,
            events=sorted(events, key=_report_date, reverse=True),
            source="finnhub",
        )

    def _fetch_historical_from_yfinance(
        self,
        ticker: str,
        limit: int,
    ) -> HistoricalEarningsResponse:
        try:
            stock = get_ticker(ticker)
            earnings_dates = call_with_retry(
                f"earnings_dates:{ticker}",
                lambda: stock.earnings_dates,
            )
        except Exception as exc:
            raise ServiceError(
                f"yfinance earnings lookup failed for {ticker}: {exc}",
                service="yfinance",
                retryable=True,
            ) from exc

        if earnings_dates is None or earnings_dates.empty:
            raise DataNotFoundError(
                f"No historical earnings found for {ticker} via yfinance",
                service="yfinance",
            )

        events: list[EarningsEvent] = []
        for idx, row in earnings_dates.iterrows():
            report_date = idx.date() if hasattr(idx, "date") else idx
            if report_date > date.today():
                continue
            events.append(
                EarningsEvent(
                    ticker=ticker,
                    report_date=report_date,
                    report_time=self._map_hour_to_report_time(row.get("Hour")),
                    eps_estimate=self._safe_float(row.get("EPS Estimate")),
                    eps_actual=self._safe_float(row.get("Reported EPS")),
                )
            )
            if len(events) >= limit:
                break

        if not events:
            raise DataNotFoundError(
                f"No past earnings dates found for {ticker} via yfinance",
                service="yfinance",
            )

        return HistoricalEarningsResponse(
            ticker=ticker,
            events=sorted(events, key=_report_date, reverse=True),
            source="yfinance",
        )

    @staticmethod
    def _get_next_earnings_from_yfinance(ticker: str) -> date | None:
        try:
            calendar = call_with_retry(
                f"calendar:{ticker}",
                lambda: get_ticker(ticker).calendar,
            )
            if isinstance(calendar, dict):
                raw = calendar.get("Earnings Date")
                if isinstance(raw, list) and raw:
                    value = raw[0]
                    return value.date() if hasattr(value, "date") else value
                if raw is not None:
                    return raw.date() if hasattr(raw, "date") else raw
        except Exception:
            return None
        return None

    @staticmethod
    def _parse_calendar_event(item: dict) -> EarningsEvent:
        report_date = datetime.strptime(item["date"], "%Y-%m-%d").date()
        hour = item.get("hour")
        return EarningsEvent(
            ticker=item["symbol"].upper(),
            report_date=report_date,
            report_time=EarningsCalendarService._normalize_report_time(hour),
            eps_estimate=item.get("epsEstimate"),
            eps_actual=item.get("epsActual"),
            revenue_estimate=item.get("revenueEstimate"),
            revenue_actual=item.get("revenueActual"),
            quarter=item.get("quarter"),
            year=item.get("year"),
        )

    @staticmethod
    def _normalize_report_time(hour: str | None) -> str | None:
        if not hour:
            return None
        normalized = hour.strip().lower()
        if normalized in {"bmo", "before market open", "am"}:
            return "bmo"
        if normalized in {"amc", "after market close", "pm", "after hours"}:
            return "amc"
        return normalized

    @staticmethod
    def _parse_period(period: str) -> date | None:
        try:
            return datetime.strptime(period, "%Y-%m-%d").date()
        except ValueError:
            return None

    @staticmethod
    def _extract_quarter(period: str) -> int | None:
        try:
            parsed = datetime.strptime(period, "%Y-%m-%d")
            return ((parsed.month - 1) // 3) + 1
        except ValueError:
            return None

    @staticmethod
    def _extract_year(period: str) -> int | None:
        try:
            return datetime.strptime(period, "%Y-%m-%d").year
        except ValueError:
            return None

    @staticmethod
    def _map_hour_to_report_time(hour: str | None) -> str | None:
        if not hour:
            return None
        normalized = str(hour).strip().lower()
        if "before" in normalized:
            return "bmo"
        if "after" in normalized:
            return "amc"
        return normalized

    @staticmethod
    def _safe_float(value: object) -> float | None:
        if value is None or not isinstance(value, int | float | str):
            return None
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        if numeric != numeric:  # NaN
            return None
        return numeric

    async def get_peers(
        self,
        ticker: str,
        *,
        use_cache: bool = True,
    ) -> list[str]:
        """Fetch peer company tickers from Finnhub /stock/peers."""
        normalized = ticker.upper().strip()
        cache_key = TTLCache.make_key("finnhub_peers", normalized)
        if use_cache:
            cached = self._cache.get(cache_key)
            if isinstance(cached, list):
                return [peer for peer in cached if isinstance(peer, str)]

        if not self._settings.finnhub_api_key:
            return []

        owns_client = self._client is None
        client = await self._get_client()
        try:
            response = await client.get(
                f"{FINNHUB_BASE_URL}/stock/peers",
                params={
                    "symbol": normalized,
                    "token": self._settings.finnhub_api_key,
                },
            )
            response.raise_for_status()
            peers = response.json()
            if isinstance(peers, list):
                result = [
                    p.upper().strip()
                    for p in peers
                    if isinstance(p, str)
                    and p.upper().strip() != normalized
                    and len(p.strip()) <= 5
                ]
                if use_cache:
                    self._cache.set(cache_key, result, ttl_seconds=86400)
                return result
            return []
        except Exception:
            return []
        finally:
            if owns_client:
                await client.aclose()
