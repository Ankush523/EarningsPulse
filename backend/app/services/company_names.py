"""Static company name lookup — avoids yfinance .info rate limits."""

from __future__ import annotations

# Major tickers used in peer maps and demos (extend as needed).
KNOWN_COMPANY_NAMES: dict[str, str] = {
    "AAPL": "Apple Inc.",
    "NVDA": "NVIDIA Corporation",
    "AMD": "Advanced Micro Devices",
    "INTC": "Intel Corporation",
    "AVGO": "Broadcom Inc.",
    "MRVL": "Marvell Technology",
    "MU": "Micron Technology",
    "QCOM": "Qualcomm",
    "TXN": "Texas Instruments",
    "ASML": "ASML Holding",
    "ARM": "Arm Holdings",
    "LRCX": "Lam Research",
    "KLAC": "KLA Corporation",
    "AMAT": "Applied Materials",
    "ON": "ON Semiconductor",
    "MCHP": "Microchip Technology",
    "SMCI": "Super Micro Computer",
    "DELL": "Dell Technologies",
    "HPE": "Hewlett Packard Enterprise",
    "ANET": "Arista Networks",
    "TSM": "Taiwan Semiconductor",
    "MSFT": "Microsoft",
    "AMZN": "Amazon.com",
    "GOOGL": "Alphabet Inc.",
    "META": "Meta Platforms",
    "CRM": "Salesforce",
    "ORCL": "Oracle",
    "TSLA": "Tesla Inc.",
    "F": "Ford Motor",
    "GM": "General Motors",
    "RIVN": "Rivian Automotive",
    "JPM": "JPMorgan Chase",
    "BAC": "Bank of America",
    "WFC": "Wells Fargo",
    "GS": "Goldman Sachs",
    "V": "Visa Inc.",
    "MA": "Mastercard",
    "WMT": "Walmart",
    "NIO": "NIO Inc.",
    "LI": "Li Auto",
}


def get_company_name(ticker: str) -> str | None:
    """Return a known company name without hitting Yahoo quoteSummary API."""
    return KNOWN_COMPANY_NAMES.get(ticker.upper().strip())
