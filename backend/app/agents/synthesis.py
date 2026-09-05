"""Synthesis agent — assembles the complete Earnings Playbook."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

from app.agents.mappers import parse_confidence
from app.agents.trace_utils import make_trace_event, trace_to_dict
from app.models.agent_state import AgentState, ForecastResult, ResearchBundle
from app.models.playbook import (
    ActionPlaybook,
    ActionRule,
    ConfidenceTier,
    ExecutiveSummary,
    KeyMetric,
    Playbook,
    PlaybookMetadata,
    ReactionAnalysisSummary,
    ReportForecast,
    Source,
    SpilloverMap,
)
from app.models.trace import TraceEventType
from app.utils.confidence import combine_confidence

AGENT_NAME = "synthesis"


class SynthesisAgent:
    """Merge all agent outputs into a structured Playbook."""

    async def run(self, state: AgentState) -> dict[str, Any]:
        job_id = state["job_id"]
        ticker = state["ticker"].upper()
        started = time.perf_counter()

        trace_events: list[dict[str, Any]] = [
            trace_to_dict(
                make_trace_event(
                    job_id,
                    TraceEventType.AGENT_STARTED,
                    f"Synthesis agent started for {ticker}",
                    agent_name=AGENT_NAME,
                )
            )
        ]

        research: ResearchBundle = state.get("research") or {}
        forecast: ForecastResult = state.get("forecast") or _empty_forecast()
        reaction: ReactionAnalysisSummary = state.get("reaction") or _empty_reaction(ticker)
        spillover: SpilloverMap = state.get("spillover") or SpilloverMap(
            reporting_ticker=ticker, peers=[], confidence=ConfidenceTier.LOW
        )

        all_sources = _collect_sources(research, reaction, spillover)
        earnings_dt = _parse_earnings_datetime(research.get("earnings_date"))

        overall_confidence = combine_confidence(
            parse_confidence(forecast.get("confidence")),
            reaction.confidence,
            spillover.confidence,
        )

        top_drivers = _build_top_drivers(forecast, reaction)

        executive_summary = ExecutiveSummary(
            ticker=ticker,
            company_name=research.get("company_name"),
            earnings_date=earnings_dt,
            is_after_hours=research.get("is_after_hours", True),
            beat_probability=forecast["beat_probability"],
            inline_probability=forecast["inline_probability"],
            miss_probability=forecast["miss_probability"],
            primary_pattern=reaction.archetype,
            primary_pattern_description=reaction.archetype_description,
            overall_confidence=overall_confidence,
            top_drivers=top_drivers,
            sources=all_sources[:5],
        )

        report_forecast = ReportForecast(
            key_metrics=[
                KeyMetric(
                    name=m["name"],
                    description=m["description"],
                    importance=parse_confidence(m.get("importance", "medium")),
                )
                for m in forecast.get("key_metrics", [])
            ],
            bull_case=forecast["bull_case"],
            base_case=forecast["base_case"],
            bear_case=forecast["bear_case"],
            positive_surprises=forecast.get("positive_surprises", []),
            negative_surprises=forecast.get("negative_surprises", []),
            confidence=parse_confidence(forecast.get("confidence")),
            sources=[s for s in all_sources if s.source_type in {"tavily", "edgar"}][:5],
        )

        action_playbook = _build_action_playbook(forecast, reaction)

        generation_time_ms = int((time.perf_counter() - started) * 1000)

        playbook = Playbook(
            metadata=PlaybookMetadata(
                job_id=job_id,
                generation_time_ms=generation_time_ms,
                data_sources_used=_data_sources_used(research, reaction, spillover),
            ),
            executive_summary=executive_summary,
            report_forecast=report_forecast,
            reaction_analysis=reaction,
            spillover_map=spillover,
            action_playbook=action_playbook,
            all_sources=all_sources,
            trace_id=job_id,
        )

        trace_events.append(
            trace_to_dict(
                make_trace_event(
                    job_id,
                    TraceEventType.AGENT_COMPLETED,
                    f"Synthesis agent completed for {ticker}",
                    agent_name=AGENT_NAME,
                    output_summary={"sections": 6, "sources": len(all_sources)},
                    latency_ms=generation_time_ms,
                )
            )
        )

        return {
            "playbook": playbook,
            "trace_events": trace_events,
            "status": "completed",
            "current_agent": AGENT_NAME,
        }


def _build_action_playbook(
    forecast: ForecastResult,
    reaction: ReactionAnalysisSummary,
) -> ActionPlaybook:
    rules: list[ActionRule] = []
    beat_prob = forecast.get("beat_probability", 0.33)
    dip_zone = reaction.expected_dip_zone or {}
    min_dip = dip_zone.get("min", -3.0)
    max_dip = dip_zone.get("max", -1.0)

    if reaction.archetype.value == "dip_then_rally":
        rules.append(
            ActionRule(
                condition=(
                    f"If beat confirmed AND price dips between {min_dip:.1f}% "
                    f"and {max_dip:.1f}% from pre-earnings close"
                ),
                action="Historically a reversal zone — watch for entry on stabilization.",
                confidence=ConfidenceTier.MEDIUM,
                historical_basis=reaction.archetype_description,
            )
        )
    elif reaction.archetype.value == "immediate_rip":
        rules.append(
            ActionRule(
                condition="If beat confirmed with strong guidance",
                action="Expect immediate upward move — waiting for a dip may cause a missed entry.",
                confidence=ConfidenceTier.MEDIUM,
                historical_basis=reaction.archetype_description,
            )
        )

    rules.append(
        ActionRule(
            condition="If miss or weak guidance",
            action="Avoid dip-buy assumption — gap-down scenarios historically dominate.",
            confidence=ConfidenceTier.MEDIUM,
            historical_basis="Gap-and-hold or volatility patterns on negative surprises",
        )
    )

    if beat_prob >= 0.5:
        rules.append(
            ActionRule(
                condition=f"If beat probability holds ({beat_prob:.0%})",
                action="Bias toward constructive setup but confirm with initial price action.",
                confidence=ConfidenceTier.MEDIUM,
            )
        )

    return ActionPlaybook(rules=rules)


def _build_top_drivers(
    forecast: ForecastResult,
    reaction: ReactionAnalysisSummary,
) -> list[str]:
    drivers = []
    if forecast.get("key_metrics"):
        drivers.append(f"Watch {forecast['key_metrics'][0]['name']}")
    drivers.append(f"Historical pattern: {reaction.archetype.value.replace('_', ' ')}")
    if reaction.backtest_years is not None:
        drivers.append(
            f"Backtested {len(reaction.historical_reactions)} earnings over "
            f"{reaction.backtest_years:.1f} years"
        )
    if reaction.dip_frequency_on_positive is not None:
        drivers.append(f"Dip-on-positive frequency: {reaction.dip_frequency_on_positive:.0%}")
    if forecast.get("bull_case"):
        drivers.append(forecast["bull_case"][:120])
    return drivers[:5] or ["Earnings sentiment", "Historical reaction pattern", "Sector context"]


def _collect_sources(
    research: ResearchBundle,
    reaction: ReactionAnalysisSummary,
    spillover: SpilloverMap,
) -> list[Source]:
    sources: list[Source] = []
    seen: set[str] = set()

    for item in research.get("sources", []):
        url = item.get("url", "")
        if url and url not in seen:
            seen.add(url)
            sources.append(
                Source(
                    title=item.get("title", "Source"),
                    url=url,
                    source_type=item.get("source_type", "tavily"),
                )
            )

    for src_list in (reaction.sources, spillover.sources):
        for src in src_list:
            if src.url not in seen:
                seen.add(src.url)
                sources.append(src)

    return sources


def _parse_earnings_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed
    except ValueError:
        try:
            parsed = datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=UTC)
            return parsed
        except ValueError:
            return None


def _data_sources_used(
    research: ResearchBundle,
    reaction: ReactionAnalysisSummary,
    spillover: SpilloverMap,
) -> list[str]:
    sources = set()
    for item in research.get("sources", []):
        sources.add(item.get("source_type", "research"))
    if reaction.historical_reactions:
        sources.add("price_data")
    if spillover.peers:
        sources.add("peer_correlation")
    return sorted(sources)


def _empty_forecast() -> ForecastResult:
    return ForecastResult(
        beat_probability=0.33,
        inline_probability=0.34,
        miss_probability=0.33,
        key_metrics=[],
        bull_case="Insufficient data.",
        base_case="Insufficient data.",
        bear_case="Insufficient data.",
        positive_surprises=[],
        negative_surprises=[],
        confidence="low",
    )


def _empty_reaction(ticker: str) -> ReactionAnalysisSummary:
    from app.models.playbook import ReactionArchetype

    return ReactionAnalysisSummary(
        archetype=ReactionArchetype.INSUFFICIENT_DATA,
        archetype_description=f"Insufficient reaction data for {ticker}.",
        confidence=ConfidenceTier.LOW,
    )
