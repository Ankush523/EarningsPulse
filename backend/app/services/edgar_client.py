"""SEC EDGAR wrapper for filing metadata."""

from __future__ import annotations

from datetime import date, datetime

import httpx

from app.config import Settings, get_settings
from app.models.data import EdgarFiling, EdgarFilingsResponse, FilingType
from app.services.errors import DataNotFoundError, ServiceError
from app.utils.cache import TTLCache, app_cache

SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_FILING_URL = (
    "https://www.sec.gov/Archives/edgar/data/{cik_numeric}/{accession_no_dashes}/{primary_doc}"
)


class EdgarClient:
    """Fetch SEC EDGAR filing metadata."""

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
        return httpx.AsyncClient(
            timeout=45.0,
            headers={"User-Agent": self._user_agent},
        )

    @property
    def _user_agent(self) -> str:
        return self._settings.sec_user_agent

    async def get_filings(
        self,
        ticker: str,
        *,
        use_cache: bool = True,
    ) -> EdgarFilingsResponse:
        """Fetch latest quarterly and annual filings for a ticker."""
        normalized = ticker.upper().strip()
        cache_key = TTLCache.make_key("edgar_filings", normalized)

        if use_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        company = await self._resolve_company(normalized)
        submissions = await self._fetch_submissions(company["cik_padded"])

        recent = submissions.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        filing_dates = recent.get("filingDate", [])
        accession_numbers = recent.get("accessionNumber", [])
        primary_documents = recent.get("primaryDocument", [])
        report_dates = recent.get("reportDate", [])

        if not forms:
            raise DataNotFoundError(
                f"No EDGAR filings found for {normalized}",
                service="edgar",
            )

        filings: list[EdgarFiling] = []
        for idx, form in enumerate(forms):
            if form not in {
                FilingType.TEN_Q.value,
                FilingType.TEN_K.value,
                FilingType.EIGHT_K.value,
            }:
                continue

            filing_date = self._parse_date(filing_dates[idx])
            if filing_date is None:
                continue

            accession = accession_numbers[idx]
            primary_doc = primary_documents[idx]
            cik_numeric = str(int(company["cik_padded"]))

            filings.append(
                EdgarFiling(
                    ticker=normalized,
                    cik=company["cik_padded"],
                    company_name=company["title"],
                    form_type=FilingType(form),
                    filing_date=filing_date,
                    report_date=self._parse_date(report_dates[idx])
                    if idx < len(report_dates)
                    else None,
                    accession_number=accession,
                    document_url=SEC_FILING_URL.format(
                        cik_numeric=cik_numeric,
                        accession_no_dashes=accession.replace("-", ""),
                        primary_doc=primary_doc,
                    ),
                    description=form,
                )
            )

            if len(filings) >= 12:
                break

        if not filings:
            raise DataNotFoundError(
                f"No 10-Q/10-K/8-K filings found for {normalized}",
                service="edgar",
            )

        latest_quarterly = next(
            (f for f in filings if f.form_type == FilingType.TEN_Q),
            None,
        )
        latest_annual = next(
            (f for f in filings if f.form_type == FilingType.TEN_K),
            None,
        )

        result = EdgarFilingsResponse(
            ticker=normalized,
            cik=company["cik_padded"],
            company_name=company["title"],
            latest_quarterly=latest_quarterly,
            latest_annual=latest_annual,
            recent_filings=filings,
        )

        if use_cache:
            self._cache.set(cache_key, result, ttl_seconds=86400)

        return result

    async def _resolve_company(self, ticker: str) -> dict[str, str]:
        cache_key = TTLCache.make_key("sec_ticker_map")
        ticker_map: dict[str, dict] | None = self._cache.get(cache_key)

        if ticker_map is None:
            ticker_map = await self._fetch_ticker_map()
            self._cache.set(cache_key, ticker_map, ttl_seconds=86400)

        company = ticker_map.get(ticker)
        if company is None:
            raise DataNotFoundError(
                f"Ticker {ticker} not found in SEC company tickers map",
                service="edgar",
            )
        return company

    async def _fetch_ticker_map(self) -> dict[str, dict]:
        owns_client = self._client is None
        client = await self._get_client()

        try:
            response = await client.get(SEC_TICKERS_URL)
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError as exc:
            raise ServiceError(
                f"Failed to fetch SEC ticker map: {exc}",
                service="edgar",
                retryable=True,
            ) from exc
        finally:
            if owns_client:
                await client.aclose()

        mapping: dict[str, dict] = {}
        for entry in payload.values():
            symbol = str(entry.get("ticker", "")).upper()
            cik = str(entry.get("cik_str", ""))
            if not symbol or not cik:
                continue
            mapping[symbol] = {
                "ticker": symbol,
                "cik_padded": cik.zfill(10),
                "title": entry.get("title", symbol),
            }
        return mapping

    async def _fetch_submissions(self, cik_padded: str) -> dict:
        owns_client = self._client is None
        client = await self._get_client()

        try:
            response = await client.get(
                SEC_SUBMISSIONS_URL.format(cik=cik_padded),
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise DataNotFoundError(
                    f"SEC submissions not found for CIK {cik_padded}",
                    service="edgar",
                ) from exc
            raise ServiceError(
                f"SEC submissions request failed: {exc.response.text}",
                service="edgar",
                retryable=exc.response.status_code >= 500,
            ) from exc
        except httpx.HTTPError as exc:
            raise ServiceError(
                f"SEC submissions request failed: {exc}",
                service="edgar",
                retryable=True,
            ) from exc
        finally:
            if owns_client:
                await client.aclose()

    @staticmethod
    def _parse_date(value: str | None) -> date | None:
        if not value:
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None
