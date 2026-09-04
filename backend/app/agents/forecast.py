"""Forecast agent — beat/miss probabilities and narrative cases."""

from __future__ import annotations

import time
from typing import Any

from app.agents.llm import LLMClient
from app.agents.trace_utils import make_trace_event, trace_to_dict
from app.models.agent_state import AgentState, ForecastResult, ResearchBundle
from app.models.trace import TraceEventType

AGENT_NAME = "forecast"

FORECAST_SYSTEM_PROMPT = """You are a financial analyst preparing a pre-earnings forecast.
Return ONLY valid JSON with these keys:
beat_probability, inline_probability, miss_probability (must sum to ~1.0),
key_metrics (list of {name, description, importance: high|medium|low}),
bull_case, base_case, bear_case (strings),
positive_surprises (list of strings), negative_surprises (list of strings),
confidence (high|medium|low).
Do not predict exact EPS numbers. Be directional and qualitative."""

FORECAST_USER_TEMPLATE = """Ticker: {ticker}
Company: {company}
Earnings date: {earnings_date}

Last earnings summary:
{last_earnings_summary}

Analyst context:
{analyst_context}

Sector context:
{sector_context}

Recent headlines:
{headlines}
"""


class ForecastAgent:
    """Forecast report sentiment from research bundle."""

    def __init__(self, llm: LLMClient | None = None):
        self._llm = llm or LLMClient()

    async def run(self, state: AgentState) -> dict[str, Any]:
        job_id = state["job_id"]
        ticker = state["ticker"].upper()
        research = state.get("research") or {}
        started = time.perf_counter()

        trace_events: list[dict[str, Any]] = [
            trace_to_dict(
                make_trace_event(
                    job_id,
                    TraceEventType.AGENT_STARTED,
                    f"Forecast agent started for {ticker}",
                    agent_name=AGENT_NAME,
                )
            )
        ]

        fallback = _heuristic_forecast(research)
        headlines = (
            "\n".join(f"- {n.get('title', '')}" for n in research.get("recent_news", [])[:5])
            or "- No recent headlines"
        )

        user_prompt = FORECAST_USER_TEMPLATE.format(
            ticker=ticker,
            company=research.get("company_name") or ticker,
            earnings_date=research.get("earnings_date") or "unknown",
            last_earnings_summary=research.get("last_earnings_summary", ""),
            analyst_context=research.get("analyst_context", ""),
            sector_context=research.get("sector_context", ""),
            headlines=headlines,
        )

        result = await self._llm.invoke_json(
            system_prompt=FORECAST_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            fallback=fallback,
        )
        forecast = _normalize_forecast(result, fallback)

        trace_events.append(
            trace_to_dict(
                make_trace_event(
                    job_id,
                    TraceEventType.AGENT_COMPLETED,
                    f"Forecast agent completed for {ticker}",
                    agent_name=AGENT_NAME,
                    output_summary={
                        "beat_probability": forecast.get("beat_probability"),
                        "confidence": forecast.get("confidence"),
                    },
                    latency_ms=int((time.perf_counter() - started) * 1000),
                )
            )
        )

        return {
            "forecast": forecast,
            "trace_events": trace_events,
            "current_agent": AGENT_NAME,
        }


def _heuristic_forecast(research: ResearchBundle) -> dict[str, Any]:
    """Deterministic forecast when LLM is unavailable."""
    ticker = research.get("ticker", "TICKER")
    news = research.get("recent_news", [])
    text = " ".join(
        [research.get("analyst_context", ""), research.get("sector_context", "")]
        + [n.get("title", "") + " " + n.get("content", "") for n in news]
    ).lower()

    positive_words = ["beat", "strong", "growth", "raise", "upside", "record", "demand"]
    negative_words = ["miss", "weak", "cut", "downgrade", "concern", "slowdown", "pressure"]

    pos = sum(1 for w in positive_words if w in text)
    neg = sum(1 for w in negative_words if w in text)

    if pos > neg + 1:
        beat, inline, miss = 0.55, 0.28, 0.17
        bull = (
            f"{ticker} likely benefits from positive sector momentum "
            "and recent constructive headlines."
        )
    elif neg > pos + 1:
        beat, inline, miss = 0.22, 0.33, 0.45
        bull = f"{ticker} could still beat lowered expectations if guidance stabilizes."
    else:
        beat, inline, miss = 0.38, 0.37, 0.25
        bull = f"{ticker} has a balanced setup with mixed signals into the print."

    return {
        "beat_probability": beat,
        "inline_probability": inline,
        "miss_probability": miss,
        "key_metrics": [
            {
                "name": "Revenue growth",
                "description": "Top-line trend vs consensus",
                "importance": "high",
            },
            {
                "name": "Guidance tone",
                "description": "Forward outlook for next quarter/year",
                "importance": "high",
            },
            {
                "name": "Margins",
                "description": "Operating leverage and cost control",
                "importance": "medium",
            },
        ],
        "bull_case": bull,
        "base_case": f"{ticker} reports in line with consensus with neutral guidance.",
        "bear_case": f"{ticker} misses on key metrics or lowers guidance, triggering selloff.",
        "positive_surprises": ["Stronger than expected guidance", "Margin expansion"],
        "negative_surprises": ["Revenue miss", "Weak forward outlook"],
        "confidence": "medium" if news else "low",
    }


def _normalize_forecast(result: dict[str, Any], fallback: dict[str, Any]) -> ForecastResult:
    beat = float(result.get("beat_probability", fallback["beat_probability"]))
    inline = float(result.get("inline_probability", fallback["inline_probability"]))
    miss = float(result.get("miss_probability", fallback["miss_probability"]))
    total = beat + inline + miss
    if total <= 0:
        beat, inline, miss = (
            fallback["beat_probability"],
            fallback["inline_probability"],
            fallback["miss_probability"],
        )
    else:
        beat, inline, miss = beat / total, inline / total, miss / total

    return ForecastResult(
        beat_probability=round(beat, 4),
        inline_probability=round(inline, 4),
        miss_probability=round(miss, 4),
        key_metrics=result.get("key_metrics") or fallback["key_metrics"],
        bull_case=str(result.get("bull_case") or fallback["bull_case"]),
        base_case=str(result.get("base_case") or fallback["base_case"]),
        bear_case=str(result.get("bear_case") or fallback["bear_case"]),
        positive_surprises=result.get("positive_surprises") or fallback["positive_surprises"],
        negative_surprises=result.get("negative_surprises") or fallback["negative_surprises"],
        confidence=str(result.get("confidence") or fallback["confidence"]),
    )
