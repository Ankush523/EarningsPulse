"""Pydantic schemas for data layer service responses."""

from datetime import UTC, date, datetime
from enum import Enum

from pydantic import BaseModel, Field


class OHLCVBar(BaseModel):
    """Single OHLCV price bar."""

    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int | None = None


class PriceReturnMetrics(BaseModel):
    """Return metrics for a price window."""

    start_price: float
    end_price: float
    high_price: float
    low_price: float
    total_return_pct: float
    max_drawdown_pct: float
    max_gain_pct: float


class EarningsWindowPrices(BaseModel):
    """Price data around a single earnings date."""

    ticker: str
    earnings_date: date
    window_days: int
    bars: list[OHLCVBar]
    metrics: PriceReturnMetrics | None = None


class EarningsEvent(BaseModel):
    """A single earnings event."""

    ticker: str
    report_date: date
    report_time: str | None = Field(
        default=None, description="bmo (before market), amc (after close), or unknown"
    )
    eps_estimate: float | None = None
    eps_actual: float | None = None
    revenue_estimate: float | None = None
    revenue_actual: float | None = None
    quarter: int | None = None
    year: int | None = None


class EarningsCalendarResponse(BaseModel):
    """Upcoming earnings calendar."""

    from_date: date
    to_date: date
    events: list[EarningsEvent]


class HistoricalEarningsResponse(BaseModel):
    """Historical earnings dates for a ticker."""

    ticker: str
    events: list[EarningsEvent] = Field(default_factory=list)
    source: str = Field(description="finnhub or yfinance")


class TavilySearchResult(BaseModel):
    """Single Tavily search result."""

    title: str
    url: str
    content: str
    score: float | None = None
    published_date: str | None = None


class TavilySearchResponse(BaseModel):
    """Tavily search response."""

    query: str
    results: list[TavilySearchResult] = Field(default_factory=list)
    answer: str | None = None
    response_time: float | None = None


class FilingType(str, Enum):
    TEN_Q = "10-Q"
    TEN_K = "10-K"
    EIGHT_K = "8-K"


class EdgarFiling(BaseModel):
    """SEC EDGAR filing metadata."""

    ticker: str
    cik: str
    company_name: str
    form_type: FilingType
    filing_date: date
    report_date: date | None = None
    accession_number: str
    document_url: str
    description: str | None = None


class EdgarFilingsResponse(BaseModel):
    """SEC EDGAR filings for a company."""

    ticker: str
    cik: str
    company_name: str
    latest_quarterly: EdgarFiling | None = None
    latest_annual: EdgarFiling | None = None
    recent_filings: list[EdgarFiling] = Field(default_factory=list)
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
