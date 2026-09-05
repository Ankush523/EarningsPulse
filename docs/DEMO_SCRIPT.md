# EarningsPulse 3-minute demo script

**Event:** AI x FINANCE HACKATHON – MONEY TALKS  
**Duration:** 3:00  
**Tagline:** Know the report. Read the reaction. Watch the ripple.

## Before you go on stage

- [ ] Production URLs open in browser tabs (home + one completed playbook)
- [ ] Demo AAPL tested 3× on production (`scripts/verify_deployment.sh`)
- [ ] Optional: one live generation pre-warmed for your chosen ticker
- [ ] PRISM dashboard open if credentials are available
- [ ] Fallback: stay on Demo AAPL if WiFi or APIs fail

Recommended demo ticker: AAPL (cached) or whatever reports that evening (live).

## Minute 0:00–0:30. Problem

> "After-hours earnings are chaotic. You get a headline, beat or miss, but the stock doesn't always move the way you'd expect. A good report can dip first and rally later. And while you're watching one ticker, three peers in the same sector are moving in sympathy. EarningsPulse closes that gap."

**Screen:** Home page, hero visible, disclaimer at the top.

**Point at:** Ticker input and the three step cards (Research → Forecast → Playbook).

## Minute 0:30–1:30. Live run

> "Let me show you. I'm preparing for Apple's next earnings event."

**Action:** Click Demo AAPL (instant, reliable), or type a live ticker and click Generate Playbook if APIs are confirmed working.

**While loading (live path only):**

> "Five agents are running in parallel: research, forecast, reaction modeling, peer spillover, and synthesis. You can watch every tool call in real time."

**Screen:** Agent trace panel on the left, playbook skeleton on the right.

**If using Demo AAPL:**

> "We also ship an instant demo cache with the same playbook structure and zero API latency, so the demo never depends on venue WiFi."

## Minute 1:30–2:00. PRISM walkthrough

> "Every step is observable. Here's the research agent pulling live web sources and SEC filings. The reaction agent classified historical patterns, including dip-then-rally. The spillover agent mapped correlated peers."

**Screen:** Scroll the trace panel; highlight two or three tool calls with sources.

**If PRISM is connected:**

> "The full trajectory syncs to Block Convey PRISM for audit and replay."

**If PRISM is unavailable:**

> "Traces are stored locally in the same PRISM-compatible format, ready to sync when credentials show up."

## Minute 2:00–2:45. Playbook highlights

Scroll the completed playbook. Hit these four beats:

1. Report forecast: beat/miss probabilities, key metrics, confidence tier  
   > "We're not predicting exact EPS. We're forecasting sentiment and scenario probabilities with cited sources."

2. Price reaction scenarios: reaction workspace chart + primary pattern (for example dip-then-rally)  
   > "Daily candles around the print, with historical path overlays. This ticker historically dips on beats before recovering. That's the non-obvious part."

3. Peer spillover map: top 3–5 correlated tickers  
   > "These peers historically move in the same after-hours window."

4. Action playbook: if/then scenario tree  
   > "Structured decision support. Not financial advice."

Optional: click Export JSON or Print / PDF to show the deliverable.

## Minute 2:45–3:00. Close

> "EarningsPulse turns scattered pre-earnings data into a structured playbook, with agent transparency, source citations, and confidence scores. Know the report. Read the reaction. Watch the ripple. Thank you."

**Screen:** Executive summary header with ticker and confidence badge.

## Fallback plans

| Failure | Recovery |
|---------|----------|
| Live generation timeout | Switch to Demo AAPL (same UI, instant) |
| Tavily / Finnhub down | Demo AAPL; mention graceful degradation on the live path |
| PRISM unavailable | Local trace panel still works; narrate from SSE events |
| Projector / browser issue | Pre-opened playbook tab as backup |

## Q&A prep (optional)

- "Is this financial advice?" No. Informational decision support only. Disclaimer on every page.
- "How accurate are predictions?" Probabilistic scenarios from historical patterns plus live research. Confidence tiers flag data quality.
- "Why not just use Bloomberg?" We synthesize a scenario playbook with reaction path modeling and peer spillover, not a static dashboard.
- "What's under the hood?" FastAPI + LangGraph multi-agent pipeline, Next.js frontend, Tavily, yfinance, Finnhub, and EDGAR.

## Rehearsal checklist

- [ ] Run through the script twice timed (target ≤ 3:00)
- [ ] Demo AAPL works on the production URL
- [ ] One live generation tested end-to-end
- [ ] Export button tested once
- [ ] Calendar page loads (optional 10s mention of upcoming earnings)
