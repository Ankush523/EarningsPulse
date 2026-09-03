# EarningsPulse — Project Specification

**Hackathon:** [AI x FINANCE HACKATHON – MONEY TALKS](https://luma.com/vljpdtre?tk=nHDjJJ)  
**Date:** September 5, 2026 · New York City  
**Track:** Money Intelligence  
**Status:** ✅ Implemented — all phases merged to `main` (September 3, 2026)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Core Insight](#3-core-insight)
4. [Product Definition](#4-product-definition)
5. [The Three Predictions](#5-the-three-predictions)
6. [Earnings Playbook Deliverable](#6-earnings-playbook-deliverable)
7. [Agent Architecture](#7-agent-architecture)
8. [Data Sources](#8-data-sources)
9. [Dip Depth Estimation (Equity-Native)](#9-dip-depth-estimation-equity-native)
10. [Earnings Reaction Archetypes](#10-earnings-reaction-archetypes)
11. [User Experience](#11-user-experience)
12. [PRISM Integration](#12-prism-integration)
13. [Trust & Compliance Layer](#13-trust--compliance-layer)
14. [Demo Narrative](#14-demo-narrative)
15. [Success Metrics](#15-success-metrics)
16. [Scope Boundaries](#16-scope-boundaries)
17. [Hackathon Alignment](#17-hackathon-alignment)
18. [Branding](#18-branding)

---

## 1. Executive Summary

**EarningsPulse** is an AI agent platform that prepares investors and traders for after-hours earnings events. Before a company reports, the system researches the ticker, forecasts likely report sentiment, models how the stock might react (including non-obvious patterns like dip-then-rally), and maps which peer stocks could move in sympathy — producing a structured **Earnings Playbook** with full reasoning, sources, and confidence scores.

**One-line pitch:**  
> Know the report. Read the reaction. Watch the ripple.

**What it is:** An AI research and scenario agent for earnings events.  
**What it is not:** A live trading bot, crypto whale tracker, or exact EPS prediction engine.

---

## 2. Problem Statement

Every week, companies release after-hours earnings reports. These events create three persistent gaps for market participants:

| Gap | Current pain |
|-----|--------------|
| **Information overload** | Last quarter report, news, estimates, and sector context are scattered across filings, news sites, and research platforms |
| **Headline vs price path mismatch** | A positive earnings report does not always produce an immediate rally; many stocks dip first, then recover |
| **Second-order effects ignored** | Traders focus on the reporting ticker and miss correlated peers that move in the same after-hours window |

Existing tools provide static data dashboards. They do not synthesize a **coherent, scenario-based pre-earnings playbook** that accounts for historical reaction patterns and peer spillover.

---

## 3. Core Insight

The original concept (from team brainstorming) identified three layers of prediction around earnings:

1. **What might be in the report** — inferred from last quarter data plus interim scraped signals
2. **How the stock will react** — direction and path, not just beat/miss
3. **Who else gets affected** — spillover to sector peers and thematic baskets

### Important clarifications

- **NVIDIA chart example:** A shared screenshot illustrated a general price path pattern (dip → rally after positive news). It is **not** project data, not hardcoded logic, and not tied to Marvell, IREN Tech, or any specific ticker. The product learns reaction patterns **per ticker from historical data**.
- **Whale tracking removed:** The original idea included crypto whale position tracking to estimate dip depth. That is **out of scope** — wrong asset class and not viable for equity earnings. Dip estimation uses **equity-native signals** (historical reactions, implied move, volatility) instead.

---

## 4. Product Definition

### Primary user

Retail and semi-professional investors/traders preparing for **after-hours earnings** on a specific ticker.

### Core workflow

```
User selects ticker(s)
    → Agent researches company & context
    → Agent forecasts report sentiment
    → Agent models price reaction scenarios
    → Agent maps peer spillover
    → User receives Earnings Playbook
```

### Output format

A single structured **Earnings Playbook** per ticker, exportable as web view and PDF/JSON.

### Disclaimers

All outputs include clear **"Not financial advice"** labeling. Recommendations are decision-support, not automated trade execution.

---

## 5. The Three Predictions

### Prediction 1 — Report Content Forecast

**Goal:** Estimate what the upcoming earnings report might contain and how the market is likely to interpret it.

**Output:**
- Beat / inline / miss **probability** with confidence score
- 3–5 **key metrics to watch** (e.g., segment revenue, gross margin, guidance tone, capex)
- **Bull case** and **bear case** narratives
- **Surprise factors** — what would move the market more than expected

**Inputs:**
- Previous quarter earnings report and call transcript
- Interim news and developments since last report
- Analyst estimate revisions and consensus
- Sector and macro context

**Constraint:** Qualitative and directional — not fake precision. Say *"likely beat driven by data center demand"* — not *"EPS will be $1.42"*.

---

### Prediction 2 — Price Reaction Forecast

**Goal:** Model how the stock might move after the report, including non-obvious paths.

**Scenarios modeled:**

| Report outcome | Possible price paths |
|----------------|---------------------|
| Beat / positive | Gap up, dip-then-rally, straight rally, sell-the-news fade |
| Miss / negative | Gap down, dead cat bounce, continued selloff |
| Inline / mixed | Volatility crush, range-bound, guidance-driven move |

**Dip-then-rally module (key differentiator):**

For each ticker, analyze historical earnings reactions:
- How often did a **positive** report lead to an initial dip?
- Average dip size (%)
- Average time to bottom (minutes/hours after release)
- Average recovery size after the dip
- Pattern classification label

**Example output:**
> "For TICKER, 4 of last 6 positive earnings saw an initial −1.8% avg dip within 45 minutes, then +3.2% avg recovery by next session open. Pattern: dip-then-rally."

---

### Prediction 3 — Peer Spillover Map

**Goal:** Identify which other stocks could move when the reporting company releases earnings.

**Output per peer:**
- Ticker and company name
- Relationship type (direct peer, supplier, customer, thematic basket)
- Historical co-movement score on past earnings of the reporting company
- Expected direction bias (same / inverse / weak)
- Conditional logic (e.g., "watch if reporting company beats on segment X")

**Example logic (generic):**
> "When Company A reports strong data center results, storage and memory peers often move in sympathy within the same after-hours window."

Peer mapping is **dynamic per ticker** — not hardcoded to any specific company pair from brainstorming.

---

## 6. Earnings Playbook Deliverable

The Playbook is the single user-facing artifact. Structure:

### Section A — Executive Summary
- Earnings date and time (after hours flag)
- Overall sentiment forecast (beat/miss/inline probabilities)
- Primary pattern expectation (e.g., "positive report + possible initial dip")
- Confidence level and top 3 drivers

### Section B — Report Forecast
- Key metrics expected to matter
- Bull / base / bear narrative
- What would surprise the market (positive and negative)

### Section C — Price Reaction Scenarios
Scenario tree with estimated probabilities:

```
IF beat + strong guidance:
  → 45% dip-then-rally (hist avg dip −2.1%)
  → 30% immediate rally
  → 25% sell-the-news fade

IF miss:
  → 60% gap down, limited recovery
  → ...
```

Each scenario includes:
- Expected direction
- Historical reference ("similar to Q2 FY25 reaction")
- Key price levels (prior close, after-hours high/low, recent support)

### Section D — Peer Spillover Map
- Top 5–10 related tickers
- Expected move direction and correlation score
- "Monitor in the same window" flag

### Section E — Action Playbook
Human-readable if/then guidance (decision support only):
- "If beat confirmed AND price dips > X% from AH open within Y minutes → historically this was a reversal zone"
- "If miss → avoid dip-buy assumption; peer sympathy likely negative"

### Section F — Sources & Audit Trail
- Every factual claim linked to source (URL, filing, data timestamp)
- PRISM agent trace reference
- Confidence tier per section

---

## 7. Agent Architecture

Multi-agent system orchestrated by a central coordinator:

```
User Input (Ticker + Earnings Date)
         │
         ▼
   Orchestrator
         │
    ┌────┴────┬────────────┬─────────────┐
    ▼         ▼            ▼             ▼
Research   Forecast    Reaction     Spillover
 Agent      Agent       Agent         Agent
    │         │            │             │
    └────┬────┴────────────┴─────────────┘
         ▼
   Synthesis Agent
         │
         ▼
   Earnings Playbook
         │
         ▼
   PRISM (observability layer)
```

### Agent responsibilities

| Agent | Responsibility | Primary tools |
|-------|---------------|---------------|
| **Research** | Gather last quarter data, recent news, analyst context | Tavily, SEC EDGAR, earnings APIs |
| **Forecast** | Beat/miss sentiment, surprise factors, key metrics | LLM + Research output |
| **Reaction** | Historical AH/PM price paths around past earnings | yfinance, earnings date API |
| **Spillover** | Peer identification and co-movement analysis | Sector map, correlation engine, Tavily |
| **Synthesis** | Merge outputs, resolve conflicts, assign confidence | LLM + all agent outputs |

### Orchestration principles
- Agents run in parallel where possible (Research + Reaction can start together)
- Synthesis waits for all upstream agents
- Failed tool calls trigger retry with fallback sources
- All steps logged to PRISM

---

## 8. Data Sources

| Data type | Source | Used by |
|-----------|--------|---------|
| Earnings calendar & dates | Finnhub / Alpha Vantage / yfinance | Orchestrator, Reaction |
| Historical OHLCV prices | yfinance | Reaction, Spillover |
| SEC filings & last ER | SEC EDGAR API + Tavily | Research |
| News & interim signals | **Tavily** (hackathon partner) | Research, Forecast |
| Analyst estimates | Free-tier API or Tavily | Forecast |
| Sector / peer mapping | Static taxonomy + LLM validation + historical correlation | Spillover |
| Options implied move (optional) | Options API (if available) | Reaction (dip sizing) |

### Data freshness requirements
- News: last 90 days since previous earnings
- Price history: last 8 earnings events minimum (or all available if fewer)
- Estimates: latest consensus before report date

---

## 9. Dip Depth Estimation (Equity-Native)

Whale tracking is removed. Dip depth uses explainable equity signals:

| Signal | Weight | Description |
|--------|--------|-------------|
| **Historical dip stats** | Primary | Avg/max/min dip on past positive earnings; time-to-bottom distribution |
| **Implied move** | Secondary | Options market priced-in range (if data available) |
| **Estimate dispersion** | Tertiary | High analyst disagreement → larger post-earnings swings |
| **Pre-earnings run-up** | Tertiary | Large run into earnings → higher sell-the-news dip probability |
| **Volatility regime** | Tertiary | Recent ATR vs historical → scale expected move size |

**Output format:**
> "Expected dip zone (if beat): −1.5% to −3.0% (based on last 8 earnings reactions; implied move ±4.2%)"

All estimates include confidence tier and data backing.

---

## 10. Earnings Reaction Archetypes

The system classifies each ticker into a reaction pattern based on historical data:

| Archetype | Behavior | Playbook hint |
|-----------|----------|---------------|
| **Dip-Then-Rally** | Positive report → initial selloff → recovery | Watch for dip entry zone |
| **Immediate Rip** | Positive report → straight up | Don't wait for a dip that may not come |
| **Sell the News** | Positive report → fade from highs | Avoid chasing after-hours highs |
| **Gap & Hold** | Miss → down, stays down | No dip-buy assumption |
| **Volatility Pin** | Inline → chop both directions | Reduce size or wait for clarity |

Archetypes are **computed per ticker** from historical data. The dip-then-rally pattern observed in brainstorming (NVIDIA chart example) maps to the **Dip-Then-Rally** archetype — not hardcoded.

---

## 11. User Experience

### Screen 1 — Input
- Ticker search with autocomplete
- Upcoming earnings calendar ("reporting this week")
- "Generate Playbook" action

### Screen 2 — Agent Run (live)
- PRISM panel: step-by-step agent trace
- Visible tool calls (Tavily searches, price pulls, peer lookups)
- Progress indicator: Research → Forecast → Reaction → Spillover → Synthesis

### Screen 3 — Playbook Output
- Executive summary card
- Expandable scenario tree
- Historical reaction chart (last 4–8 earnings marked on price timeline)
- Peer spillover table with correlation scores
- Sources sidebar with clickable links

### Screen 4 — Compare (stretch)
- Side-by-side playbooks for two tickers reporting the same night

### Export
- PDF download
- JSON export (for programmatic use)

---

## 12. PRISM Integration

PRISM (Block Convey) is a **required** hackathon component. Integration is core to the product, not an add-on.

### What gets logged
- Every agent step and state transition
- All tool calls (query, response summary, latency)
- Errors and retry attempts
- Confidence score changes as new data arrives
- Final synthesis reasoning chain

### Demo value
- Show where the agent failed and recovered (e.g., wrong peer initially → validation corrected it)
- Prove traceability for finance audience
- Narrative: *"We built an observable agent that finance users can trust because every recommendation is traceable."*

### PRISM workflow loop
```
Build → Observe → Improve → Prove → Demo
```

---

## 13. Trust & Compliance Layer

Optional bonus alignment with Regodit (Trust & Risk track sponsor):

| Feature | Implementation |
|---------|---------------|
| Disclaimer | Persistent "Not financial advice" banner |
| Confidence tiers | `high (data-backed)` / `medium (inferred)` / `low (speculative)` |
| Source requirements | No unsourced numerical claims |
| Audit export | PDF/JSON bundle of playbook + PRISM trace |
| Claim validation | Synthesis agent flags unsourced or contradictory claims |

---

## 14. Demo Narrative

**Duration:** 3 minutes

1. **Problem (30s):** "After-hours earnings are chaotic. Good news doesn't always mean up first — many stocks dip before they rally."
2. **Live run (60s):** Select a ticker reporting tonight → agent generates playbook in ~60–90 seconds.
3. **PRISM walkthrough (30s):** Show research sources, reaction stats, peer mapping steps.
4. **Output highlight (45s):** Beat probability, dip-then-rally pattern, peer watchlist, scenario tree.
5. **Close (15s):** "EarningsPulse turns scattered data into a pre-earnings decision playbook — with full transparency."

No dependency on specific tickers (NVIDIA, Marvell, IREN) unless they happen to be that night's demo candidates.

---

## 15. Success Metrics

| Metric | Target |
|--------|--------|
| Playbook generation time | < 2 minutes per ticker |
| Source coverage | 100% of factual claims cited |
| Historical pattern accuracy | Correctly labels past reactions on backtest tickers |
| Peer map relevance | ≥ 3 materially correlated peers for major tickers |
| PRISM trace completeness | Every tool call logged |
| Demo reliability | 3 consecutive live runs without failure |
| UI polish | Production-ready, responsive, dark/light theme |

---

## 16. Scope Boundaries

### In scope
- Pre-earnings research and scenario playbook generation
- Historical earnings reaction pattern analysis
- Peer spillover mapping with correlation scores
- PRISM-observable multi-agent system
- Web UI with live agent trace
- PDF/JSON export
- Earnings calendar view

### Out of scope
- Crypto / whale tracking
- Live order execution or brokerage integration
- Exact EPS/revenue number prediction
- Hardcoded ticker-specific logic from brainstorming examples
- Intraday HFT signals
- Mobile native app (responsive web is sufficient)

---

## 17. Hackathon Alignment

| Hackathon requirement | EarningsPulse fit |
|----------------------|-------------------|
| Real fintech problem | After-hours earnings preparation |
| AI agent product | Multi-agent research + synthesis system |
| PRISM observability | Full agent trace logging |
| Tavily partner tech | Live web research backbone |
| Money Intelligence track | Investing, market research, financial analysis |
| Demo to finance professionals | Playbook output they'd actually use |
| One-day build | Scoped MVP with production-quality execution |

### Sponsor technology usage

| Partner | Role in EarningsPulse |
|---------|----------------------|
| **Tavily** | News scraping, interim signal gathering, peer context |
| **PRISM (Block Convey)** | Agent observability and demo narrative |
| **Prelint** (optional) | Validate agent output against product requirements |
| **GIDE** (optional) | Local AI coding environment during build |

---

## 18. Branding

**Product name:** EarningsPulse  
**Tagline:** Know the report. Read the reaction. Watch the ripple.

**Alternative names (not selected):**
- EarningsOracle
- AfterHours AI
- ReportRipple

**Visual identity (to be defined during implementation):**
- Finance-professional aesthetic
- Dark theme primary (trader-friendly)
- Accent color for confidence tiers (green/amber/red)
- Clean typography, data-dense but readable layouts

---

*Document version: 1.0 · Created: September 3, 2026*
