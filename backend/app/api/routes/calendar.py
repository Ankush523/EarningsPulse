"""Earnings calendar API routes."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.api.deps import get_earnings_service
from app.models.data import EarningsCalendarResponse
from app.services.earnings_calendar import EarningsCalendarService
from app.services.errors import ConfigurationError

router = APIRouter(prefix="/calendar", tags=["calendar"])


class TickerEarningsResponse(BaseModel):
    """Earnings date response for a single ticker."""

    ticker: str
    report_date: date | None = None
    report_time: str | None = None
    has_upcoming: bool = False
    eps_estimate: float | None = None
    eps_actual: float | None = None


@router.get("", response_model=EarningsCalendarResponse)
async def get_upcoming_earnings(
    days: int = Query(default=7, ge=1, le=30),
    earnings_service: EarningsCalendarService = Depends(get_earnings_service),
) -> EarningsCalendarResponse:
    """Return earnings events scheduled for the next N days."""
    try:
        return await earnings_service.get_upcoming_earnings(days=days)
    except ConfigurationError:
        today = date.today()
        return EarningsCalendarResponse(from_date=today, to_date=today, events=[])


@router.get("/{ticker}", response_model=TickerEarningsResponse)
async def get_ticker_earnings(
    ticker: str,
    earnings_service: EarningsCalendarService = Depends(get_earnings_service),
) -> TickerEarningsResponse:
    """Return the next earnings date for a specific ticker."""
    normalized = ticker.upper().strip()
    next_date = await earnings_service.get_next_earnings_date(normalized)

    if next_date is None:
        return TickerEarningsResponse(ticker=normalized, has_upcoming=False)

    return TickerEarningsResponse(
        ticker=normalized,
        report_date=next_date,
        report_time="amc",
        has_upcoming=True,
    )
