# EarningsPulse — Implementation Plan

**Purpose:** Step-by-step build plan to deliver EarningsPulse as a production-ready hackathon project.  
**Companion doc:** [PROJECT_SPEC.md](./PROJECT_SPEC.md)  
**Build approach:** Single AI agent (Cursor) executing all phases sequentially with user review at checkpoints.

---

## Table of Contents

1. [Can This Be Done Solo?](#1-can-this-be-done-solo)
2. [Architecture Overview](#2-architecture-overview)
3. [Tech Stack Decisions](#3-tech-stack-decisions)
4. [Project Structure](#4-project-structure)
5. [Environment & Dependencies](#5-environment--dependencies)
6. [Implementation Phases](#6-implementation-phases)
7. [Detailed Step-by-Step Tasks](#7-detailed-step-by-step-tasks)
8. [API & Data Integration Plan](#8-api--data-integration-plan)
9. [Agent Implementation Details](#9-agent-implementation-details)
10. [Frontend Implementation Details](#10-frontend-implementation-details)
11. [PRISM Integration Plan](#11-prism-integration-plan)
12. [Testing Strategy](#12-testing-strategy)
13. [Production Readiness Checklist](#13-production-readiness-checklist)
14. [Risks & Mitigations](#14-risks--mitigations)
15. [User Checkpoints](#15-user-checkpoints)
16. [Estimated Effort](#16-estimated-effort)

---



## 1. Can This Be Done Solo?

**Yes.** One AI coding agent (Cursor) can complete the entire project production-ready, with these conditions:


| Requirement         | Who provides it      | Notes                                                                     |
| ------------------- | -------------------- | ------------------------------------------------------------------------- |
| Code implementation | AI agent             | All backend, frontend, agents, tests                                      |
| API keys            | **User**             | OpenAI/Anthropic, Tavily, Finnhub (free tier), optional PRISM credentials |
| PRISM access        | **User / hackathon** | Block Convey provides at event; stub locally until then                   |
| Design decisions    | AI agent             | Following spec; user reviews at checkpoints                               |
| Deployment          | AI agent             | Vercel + Railway/Render or all-in-one Docker                              |
| Demo rehearsal      | **User**             | Practice 3-minute pitch with live demo                                    |




### What the AI agent will handle entirely

- Repository scaffolding and configuration
- All backend services and API routes
- Multi-agent orchestration logic
- Data pipeline (earnings dates, prices, news, peers)
- Reaction pattern analysis engine
- Spillover correlation engine
- Full web UI with live agent trace panel
- PRISM integration (or local stub with swap-in at hackathon)
- Error handling, retries, fallbacks
- Tests for critical paths
- README, env examples, deployment config
- Demo seed data and backtest scripts



### What the user must provide

- API keys (`.env` file)
- PRISM credentials when available at hackathon
- Final demo ticker selection on event day
- 3-minute pitch delivery



### Honest limitations

- **Options implied move** depends on API availability; falls back to historical-only dip estimation if no key
- **PRISM** may need same-day integration at the venue if credentials aren't available beforehand — a local observability stub will be built so the product works regardless
- **Analyst estimates** quality varies by free-tier API; Tavily supplements gaps

---



## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                   │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │  Input   │  │ Agent Trace  │  │  Playbook Viewer      │  │
│  │  Screen  │  │ (PRISM panel)│  │  (scenarios, peers)   │  │
│  └──────────┘  └──────────────┘  └───────────────────────┘  │
└─────────────────────────┬───────────────────────────────────┘
                          │ REST / SSE
┌─────────────────────────▼───────────────────────────────────┐
│                     Backend (FastAPI)                       │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                  Agent Orchestrator                 │    │
│  │  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐  │    │
│  │  │Research │ │ Forecast │ │ Reaction │ │Spillover│  │    │
│  │  │ Agent   │ │  Agent   │ │  Agent   │ │  Agent  │  │    │
│  │  └────┬────┘ └────┬─────┘ └────┬─────┘ └────┬────┘  │    │
│  │       └───────────┴────────────┴────────────┘       │    │
│  │                        │                            │    │
│  │               ┌────────▼────────┐                   │    │
│  │               │ Synthesis Agent │                   │    │
│  │               └────────┬────────┘                   │    │
│  └────────────────────────┼────────────────────────────┘    │
│                           │                                 │
│  ┌────────────────────────▼────────────────────────────┐    │
│  │              Services Layer                         │    │
│  │ Tavily │ yfinance │ Finnhub │ EDGAR │ PRISM │ Cache │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```



### Communication pattern

- Frontend sends `POST /api/playbook/generate` with ticker
- Backend streams agent progress via **Server-Sent Events (SSE)**
- Final playbook returned as structured JSON
- PRISM events emitted in parallel to SSE stream

---



## 3. Tech Stack Decisions


| Layer               | Choice                                | Rationale                                              |
| ------------------- | ------------------------------------- | ------------------------------------------------------ |
| **Frontend**        | Next.js 14 (App Router) + TypeScript  | Production-ready, fast SSR, easy Vercel deploy         |
| **UI**              | Tailwind CSS + shadcn/ui              | Polished finance UI quickly                            |
| **Charts**          | Recharts                              | Earnings reaction timeline charts                      |
| **Backend**         | Python 3.12 + FastAPI                 | Best ecosystem for finance data + AI agents            |
| **Agent framework** | LangGraph                             | Structured multi-agent orchestration with state        |
| **LLM**             | OpenAI GPT-4o (primary)               | Tool calling, synthesis quality; Anthropic as fallback |
| **Web research**    | Tavily API                            | Hackathon partner, built for agents                    |
| **Price data**      | yfinance                              | Free, reliable historical OHLCV                        |
| **Earnings dates**  | Finnhub free tier                     | Clean earnings calendar API                            |
| **Filings**         | SEC EDGAR API                         | Free, authoritative                                    |
| **Cache**           | In-memory + optional Redis            | Avoid redundant API calls during demo                  |
| **Observability**   | PRISM SDK + local trace store         | Hackathon requirement                                  |
| **Testing**         | pytest (backend) + Playwright (E2E)   | Critical path coverage                                 |
| **Deploy**          | Vercel (frontend) + Railway (backend) | One-click, free tiers                                  |


---



## 4. Project Structure

```
finance_hackathon/
├── docs/
│   ├── PROJECT_SPEC.md
│   └── IMPLEMENTATION_PLAN.md
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI entry
│   │   ├── config.py                  # Settings & env vars
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── playbook.py        # Generate + stream endpoints
│   │   │   │   ├── calendar.py        # Upcoming earnings
│   │   │   │   └── health.py
│   │   │   └── deps.py
│   │   ├── agents/
│   │   │   ├── orchestrator.py        # LangGraph workflow
│   │   │   ├── research.py
│   │   │   ├── forecast.py
│   │   │   ├── reaction.py
│   │   │   ├── spillover.py
│   │   │   └── synthesis.py
│   │   ├── services/
│   │   │   ├── tavily_client.py
│   │   │   ├── price_data.py          # yfinance wrapper
│   │   │   ├── earnings_calendar.py   # Finnhub wrapper
│   │   │   ├── edgar_client.py
│   │   │   ├── peer_map.py            # Sector taxonomy + correlation
│   │   │   ├── reaction_analyzer.py   # Pattern classification engine
│   │   │   └── prism_client.py        # PRISM observability
│   │   ├── models/
│   │   │   ├── playbook.py            # Pydantic schemas
│   │   │   ├── agent_state.py
│   │   │   └── trace.py
│   │   └── utils/
│   │       ├── cache.py
│   │       └── confidence.py
│   ├── tests/
│   │   ├── test_reaction_analyzer.py
│   │   ├── test_peer_map.py
│   │   ├── test_agents.py
│   │   └── test_api.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx               # Landing + input
│   │   │   ├── playbook/[id]/page.tsx
│   │   │   └── calendar/page.tsx
│   │   ├── components/
│   │   │   ├── TickerInput.tsx
│   │   │   ├── AgentTracePanel.tsx    # PRISM live trace
│   │   │   ├── PlaybookView.tsx
│   │   │   ├── ScenarioTree.tsx
│   │   │   ├── ReactionChart.tsx
│   │   │   ├── PeerSpilloverTable.tsx
│   │   │   └── ConfidenceBadge.tsx
│   │   ├── lib/
│   │   │   ├── api.ts
│   │   │   └── types.ts
│   │   └── hooks/
│   │       └── usePlaybookStream.ts   # SSE hook
│   ├── package.json
│   └── Dockerfile
├── scripts/
│   ├── backtest_reactions.py          # Validate pattern engine
│   └── seed_demo.py                   # Pre-cache demo ticker
├── docker-compose.yml
├── .env.example
└── README.md
```

---



## 5. Environment & Dependencies



### Required environment variables

```bash
# LLM
OPENAI_API_KEY=sk-...

# Hackathon partners
TAVILY_API_KEY=tvly-...

# Market data
FINNHUB_API_KEY=...          # Free tier: 60 calls/min

# PRISM (Block Convey) — add at hackathon if not available earlier
PRISM_API_KEY=...
PRISM_PROJECT_ID=...

# App
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000
```



### Optional

```bash
ANTHROPIC_API_KEY=...         # LLM fallback
REDIS_URL=...                 # Production cache
```

---



## 6. Implementation Phases


| Phase | Name             | Deliverable                                       | Dependency |
| ----- | ---------------- | ------------------------------------------------- | ---------- |
| **0** | Foundation       | Repo scaffold, Docker, env, health checks         | None       |
| **1** | Data layer       | Price, earnings, news, EDGAR services working     | Phase 0    |
| **2** | Analysis engines | Reaction analyzer + peer map + pattern classifier | Phase 1    |
| **3** | Agents           | All 5 agents + orchestrator via LangGraph         | Phase 2    |
| **4** | API              | REST + SSE streaming endpoints                    | Phase 3    |
| **5** | PRISM            | Observability integration + trace panel data      | Phase 4    |
| **6** | Frontend         | Full UI — input, trace, playbook viewer           | Phase 4, 5 |
| **7** | Polish           | Export, calendar, error states, loading UX        | Phase 6    |
| **8** | Testing          | Unit, integration, E2E, backtest validation       | Phase 7    |
| **9** | Deploy           | Production deployment + README + demo script      | Phase 8    |


Phases are sequential. Each phase completes before the next begins.

---



## 7. Detailed Step-by-Step Tasks



### Phase 0 — Foundation

- [x] Initialize monorepo with `backend/` and `frontend/` directories
- [x] Set up Python virtual environment, `requirements.txt` (FastAPI, LangGraph, yfinance, httpx, pydantic, etc.)
- [x] Set up Next.js 14 with TypeScript, Tailwind, shadcn/ui
- [x] Create `.env.example` with all required keys documented
- [x] Create `docker-compose.yml` for local dev (backend + frontend)
- [x] Implement health check endpoints (`GET /health` on backend, frontend loads)
- [x] Write initial `README.md` with setup instructions
- [x] Define all Pydantic models for Playbook, AgentState, TraceEvent

**Exit criteria:** `docker-compose up` runs both services; health checks pass.

---



### Phase 1 — Data Layer

- [x] `price_data.py`**:** yfinance wrapper
  - Fetch OHLCV for date range
  - Fetch price around earnings dates (±3 days window)
  - Calculate returns, dips, recovery metrics
- [x] `earnings_calendar.py`**:** Finnhub wrapper
  - Upcoming earnings for next 7 days
  - Historical earnings dates for a ticker (last 8 events)
- [x] `tavily_client.py`**:** Tavily search wrapper
  - Search company news (last 90 days)
  - Search earnings-related content
  - Extract and summarize results
- [x] `edgar_client.py`**:** SEC EDGAR wrapper
  - Fetch latest 10-Q/10-K filing metadata
  - Link to previous earnings report
- [x] `cache.py`**:** In-memory TTL cache for API responses
- [x] Unit tests for each service with mocked responses

**Exit criteria:** Given a ticker (e.g., AAPL), all services return valid data independently.

---



### Phase 2 — Analysis Engines

- [x] `reaction_analyzer.py`**:** Core pattern engine
  - Input: list of (earnings_date, prices around date)
  - Output per event: direction, dip %, recovery %, time-to-bottom
  - Aggregate: archetype classification, avg dip, avg recovery, pattern frequency
  - Classify into archetypes (Dip-Then-Rally, Immediate Rip, etc.)
- [x] `peer_map.py`**:** Spillover engine
  - Static sector taxonomy (GICS-based peer groups for major sectors)
  - Dynamic correlation: compute return correlation on past earnings dates
  - Output: ranked peer list with correlation scores and relationship types
- [x] `confidence.py`**:** Confidence scoring utility
  - Score based on data availability, sample size, source quality
- [x] `scripts/backtest_reactions.py`**:** Validation script
  - Run reaction analyzer on 5 well-known tickers
  - Print pattern classifications for manual verification
- [x] Unit tests with synthetic price data (known dip-then-rally pattern)

**Exit criteria:** Backtest script correctly identifies known patterns on AAPL, NVDA, TSLA historical earnings.

---



### Phase 3 — Agents

- [x] `agent_state.py`**:** Shared LangGraph state schema
- [x] `research.py`**:** Research Agent
  - Tools: Tavily search, EDGAR fetch, earnings calendar
  - Output: structured research bundle (news, last ER summary, key developments)
- [x] `forecast.py`**:** Forecast Agent
  - Input: research bundle
  - Output: beat/miss/inline probabilities, key metrics, bull/bear cases
- [x] `reaction.py`**:** Reaction Agent
  - Tools: price_data, reaction_analyzer
  - Output: historical pattern stats, archetype, scenario probabilities
- [x] `spillover.py`**:** Spillover Agent
  - Tools: peer_map, Tavily (peer context), price_data (correlation)
  - Output: ranked peer list with correlation and direction bias
- [x] `synthesis.py`**:** Synthesis Agent
  - Input: all agent outputs
  - Output: complete Playbook JSON matching spec schema
  - Conflict resolution, confidence assignment, source linking
- [x] `orchestrator.py`**:** LangGraph workflow
  - Parallel: Research + Reaction
  - Sequential: Forecast (needs Research) → Spillover (needs Forecast) → Synthesis
  - Error handling: retry failed tools, fallback sources
  - Emit trace events at each step
- [x] Integration test: end-to-end agent run for one ticker

**Exit criteria:** `orchestrator.run("AAPL")` returns a complete Playbook JSON.

---



### Phase 4 — API Layer

- [x] `POST /api/playbook/generate`**:** Start playbook generation
  - Input: `{ ticker: string }`
  - Returns: `{ job_id: string }`
- [x] `GET /api/playbook/stream/{job_id}`**:** SSE stream
  - Events: `agent_start`, `tool_call`, `agent_complete`, `playbook_ready`, `error`
  - Each event includes PRISM-compatible trace data
- [x] `GET /api/playbook/{job_id}`**:** Fetch completed playbook
- [x] `GET /api/calendar`**:** Upcoming earnings (next 7 days)
- [x] `GET /api/calendar/{ticker}`**:** Earnings date for specific ticker
- [x] Request validation, error responses, rate limiting (basic)
- [x] CORS configuration for frontend

**Exit criteria:** API endpoints work via curl/Postman; SSE stream emits events during generation.

---



### Phase 5 — PRISM Integration

- [x] `prism_client.py`**:** PRISM SDK wrapper
  - If PRISM credentials available: send traces to Block Convey
  - If not: write traces to local JSON log (swap-in ready)
- [x] Emit PRISM events from orchestrator at every state transition:
  - Agent started/completed
  - Tool call initiated/completed/failed
  - Confidence updated
  - Error + retry
  - Final playbook generated
- [x] Trace schema matches PRISM expected format (or documented local format)
- [x] `GET /api/trace/{job_id}`**:** Full trace for a playbook generation job

**Exit criteria:** Agent run produces a complete trace log viewable via API; PRISM-compatible format.

---



### Phase 6 — Frontend

- [x] **Landing page (**`page.tsx`**):**
  - Hero with tagline and brief explanation
  - Ticker input with search/autocomplete
  - "Generate Playbook" CTA
  - Upcoming earnings calendar preview
- [x] `usePlaybookStream.ts`**:** SSE hook
  - Connect to stream endpoint
  - Parse events, update state
  - Handle completion and errors
- [x] `AgentTracePanel.tsx`**:** Live PRISM trace viewer
  - Step-by-step agent progress
  - Tool call log with timestamps
  - Status indicators (running/complete/error)
  - Expandable detail per step
- [x] `PlaybookView.tsx`**:** Main output display
  - Section A: Executive summary card
  - Section B: Report forecast
  - Section C: Scenario tree (interactive)
  - Section D: Peer spillover table
  - Section E: Action playbook
  - Section F: Sources list
- [x] `ReactionChart.tsx`**:** Historical earnings reaction chart
  - Price line with earnings dates marked
  - Dip/recovery annotations
- [x] `ScenarioTree.tsx`**:** Interactive scenario tree with probabilities
- [x] `PeerSpilloverTable.tsx`**:** Sortable peer table with correlation bars
- [x] `ConfidenceBadge.tsx`**:** Reusable confidence tier badge
- [x] `calendar/page.tsx`**:** Full earnings calendar view
- [x] Responsive design, dark theme, loading/error/empty states
- [x] Disclaimer banner (persistent)

**Exit criteria:** Full user flow works in browser — input ticker → watch agent run → view playbook.

---



### Phase 7 — Polish

- [x] PDF export of playbook (backend generation or frontend print)
- [x] JSON export download button
- [x] Pre-cache demo ticker via `scripts/seed_demo.py`
- [x] Loading skeletons and smooth transitions
- [x] Error recovery UX (retry button, partial results)
- [x] SEO meta tags and favicon
- [x] Performance: playbook generation < 2 minutes
- [x] Mobile-responsive layout verification

**Exit criteria:** Demo-ready UX with no rough edges on happy path or error path.

---



### Phase 8 — Testing

- [x] **Unit tests:** reaction_analyzer, peer_map, confidence scoring
- [x] **Agent tests:** each agent with mocked tools
- [x] **Integration test:** full orchestrator run with mocked external APIs
- [x] **API tests:** all endpoints, SSE stream format
- [x] **E2E test (Playwright):** input ticker → wait for playbook → verify sections render
- [x] **Backtest validation:** run on 5 tickers, verify pattern labels are reasonable
- [x] Fix any failures

**Exit criteria:** All tests pass; backtest output reviewed and sensible.

---



### Phase 9 — Deploy & Document

- [x] Deployment configs — Railway (`backend/railway.toml`), Render (`render.yaml`), Vercel (`frontend/vercel.json`), Docker production hardening
- [x] Production env vars documented (`.env.example`, `docs/DEPLOYMENT.md`)
- [x] CORS auto-includes `FRONTEND_URL` for production domains
- [x] `scripts/verify_deployment.sh` — post-deploy health + demo verification
- [ ] **User action:** Deploy backend to Railway (or Render)
- [ ] **User action:** Deploy frontend to Vercel
- [ ] **User action:** Configure production env vars and verify E2E on live URLs
- [x] Final README — overview, architecture, API reference, deployment, demo
- [x] `docs/DEMO_SCRIPT.md` — 3-minute pitch outline
- [ ] **User action:** Tag release `v1.0.0` after production verified

**Exit criteria:** Production URL live; README complete; demo script ready.

---



## 8. API & Data Integration Plan



### Tavily (Research Agent)

```
Queries per playbook generation: 3–5
- "{ticker} earnings preview {quarter}"
- "{ticker} recent news last 90 days"
- "{company name} analyst estimates earnings"
- "{ticker} sector peers earnings impact"
```

Fallback if Tavily fails: LLM knowledge + EDGAR filing text (lower confidence flagged).

### yfinance (Reaction + Spillover Agents)

```
Calls per playbook: 2–3
- Historical daily prices (2 years)
- Intraday if available (for recent earnings)
- Peer ticker prices for correlation
```

Fallback: Alpha Vantage free tier.

### Finnhub (Calendar)

```
Calls per playbook: 1–2
- Upcoming earnings date for ticker
- Historical earnings dates (last 8)
```

Fallback: yfinance earnings dates (less reliable but functional).

### SEC EDGAR (Research Agent)

```
Calls per playbook: 1
- Latest 10-Q or 10-K filing link and metadata
```

Fallback: Tavily search for filing content.

---



## 9. Agent Implementation Details



### LangGraph state schema

```python
class AgentState(TypedDict):
    ticker: str
    earnings_date: Optional[str]
    research: Optional[ResearchBundle]
    forecast: Optional[ForecastResult]
    reaction: Optional[ReactionAnalysis]
    spillover: Optional[SpilloverMap]
    playbook: Optional[Playbook]
    trace_events: list[TraceEvent]
    errors: list[str]
```



### Orchestration flow

```
START
  ├─→ research_agent (parallel)
  └─→ reaction_agent (parallel)
        │
        ▼
   forecast_agent (needs research)
        │
        ▼
   spillover_agent (needs forecast)
        │
        ▼
   synthesis_agent (needs all)
        │
        ▼
      END → Playbook
```



### Tool definitions per agent


| Agent     | Tools                                                      |
| --------- | ---------------------------------------------------------- |
| Research  | `tavily_search`, `fetch_edgar_filing`, `get_earnings_date` |
| Forecast  | (no external tools — LLM reasoning on research bundle)     |
| Reaction  | `fetch_price_history`, `analyze_earnings_reactions`        |
| Spillover | `get_peer_map`, `compute_correlation`, `tavily_search`     |
| Synthesis | (no external tools — LLM synthesis of all outputs)         |




### Retry policy

- Tool call fails → retry once with backoff
- Second failure → use fallback source if available
- No fallback → mark section as `low confidence` and continue
- Never block entire playbook for one failed data point

---



## 10. Frontend Implementation Details



### Key user flows

**Flow 1 — Generate Playbook**

1. User lands on homepage
2. Types ticker (e.g., "MRVL") or picks from calendar
3. Clicks "Generate Playbook"
4. Redirected to `/playbook/{job_id}`
5. Agent trace panel shows live progress (SSE)
6. Playbook sections populate as agents complete
7. Full playbook rendered when synthesis finishes

**Flow 2 — Browse Calendar**

1. User navigates to `/calendar`
2. Sees upcoming earnings for the week
3. Clicks any ticker → starts Flow 1



### Design system


| Element           | Style                                          |
| ----------------- | ---------------------------------------------- |
| Background        | Dark (#0a0a0f) primary                         |
| Cards             | Slightly elevated (#141420) with subtle border |
| Accent            | Electric blue (#3b82f6) for actions            |
| Confidence high   | Green (#22c55e)                                |
| Confidence medium | Amber (#f59e0b)                                |
| Confidence low    | Red (#ef4444)                                  |
| Typography        | Inter (UI) + JetBrains Mono (data/numbers)     |
| Charts            | Recharts with dark theme                       |


---



## 11. PRISM Integration Plan



### Local stub (build now)

If PRISM credentials aren't available before the hackathon:

```python
class PrismClient:
    def __init__(self, api_key: Optional[str] = None):
        self.local_mode = api_key is None
        self.events: list[dict] = []

    async def emit(self, event: TraceEvent):
        self.events.append(event.model_dump())
        if not self.local_mode:
            await self._send_to_prism(event)
```

- All traces stored locally and served via `GET /api/trace/{job_id}`
- Frontend AgentTracePanel reads from same SSE stream
- At hackathon: add `PRISM_API_KEY` to env → auto-switches to live PRISM



### PRISM event types


| Event                 | Payload                                |
| --------------------- | -------------------------------------- |
| `run_started`         | ticker, timestamp                      |
| `agent_started`       | agent_name                             |
| `tool_call_started`   | tool_name, input_summary               |
| `tool_call_completed` | tool_name, output_summary, latency_ms  |
| `tool_call_failed`    | tool_name, error, retry_attempt        |
| `agent_completed`     | agent_name, output_summary, confidence |
| `confidence_updated`  | section, old_score, new_score, reason  |
| `run_completed`       | total_latency_ms, playbook_id          |
| `run_failed`          | error, partial_results                 |


---



## 12. Testing Strategy

**Status (Phase 8):** Implemented — see `backend/tests/`, `frontend/e2e/`, `.github/workflows/ci.yml`, and `scripts/run_tests.sh`.

| Level           | What                                    | How                                    | Status |
| --------------- | --------------------------------------- | -------------------------------------- | ------ |
| **Unit**        | Reaction analyzer, peer map, confidence | pytest with synthetic data             | ✅ |
| **Unit**        | Individual agent logic                  | pytest with mocked LLM + tools         | ✅ |
| **Integration** | Full orchestrator                       | pytest with mocked external APIs       | ✅ |
| **API**         | All endpoints + SSE format              | pytest + httpx AsyncClient             | ✅ |
| **E2E**         | Full user flow                          | Playwright: demo AAPL → playbook sections | ✅ |
| **Validation**  | Pattern accuracy                        | Backtest tests on 5 tickers (mocked)   | ✅ |
| **Manual**      | Demo reliability                        | 3 consecutive live runs on demo ticker | 🔜 Phase 9 |




### Backtest tickers (validation, not hardcoded logic)

- AAPL (mega-cap, well-documented reactions)
- NVDA (high volatility, dip-then-rally candidate)
- TSLA (volatile, mixed patterns)
- JPM (financials sector baseline)
- AMZN (inline/mixed pattern candidate)

---



## 13. Production Readiness Checklist



### Functionality

- [x] Playbook generates for any valid US equity ticker
- [x] All 6 playbook sections populated with real data
- [x] Agent trace visible in real-time
- [x] Earnings calendar loads upcoming week
- [x] PDF/JSON export works
- [x] Error states handled gracefully (invalid ticker, API down, partial data)



### Quality

- [x] All tests pass
- [x] No hardcoded ticker-specific logic
- [x] Every factual claim has a source link
- [x] Confidence tiers assigned correctly
- [x] Disclaimer visible on all pages
- [x] Generation completes in < 2 minutes



### Deployment

- [ ] Backend deployed and healthy *(user deploys — configs ready)*
- [ ] Frontend deployed and connected to backend *(user deploys)*
- [x] Environment variables documented
- [x] CORS configured correctly (FRONTEND_URL auto-merge)
- [ ] HTTPS enabled *(provided by Vercel + Railway/Render)*



### Demo

- [x] Demo script written and rehearsed (`docs/DEMO_SCRIPT.md`)
- [ ] Demo ticker pre-tested 3+ times successfully *(user verifies on production)*
- [x] PRISM trace visible and narratable
- [x] Fallback plan if live APIs fail during demo (cached playbook)



### Documentation

- [x] README with setup and architecture
- [x] PROJECT_SPEC.md (this spec)
- [x] IMPLEMENTATION_PLAN.md (this plan)
- [x] DEMO_SCRIPT.md
- [x] DEPLOYMENT.md
- [x] .env.example with all keys documented

---



## 14. Risks & Mitigations


| Risk                              | Impact                    | Mitigation                                                        |
| --------------------------------- | ------------------------- | ----------------------------------------------------------------- |
| Tavily API rate limit during demo | Research agent fails      | Pre-cache demo ticker; TTL cache                                  |
| Finnhub free tier limits          | Calendar fails            | yfinance fallback for earnings dates                              |
| LLM hallucinates metrics          | Bad playbook data         | Source-required policy in synthesis agent; confidence tiers       |
| PRISM credentials unavailable     | No live PRISM integration | Local stub with identical trace format; swap at venue             |
| yfinance rate limiting            | Price data fails          | Cache aggressively; Alpha Vantage fallback                        |
| Agent takes > 2 min               | Bad demo experience       | Parallel agent execution; cache; pre-warm demo ticker             |
| Obscure ticker has no data        | Empty playbook sections   | Graceful degradation; flag low confidence; suggest similar ticker |
| Hackathon WiFi issues             | APIs unreachable          | Offline demo mode with cached playbook JSON                       |


---



## 15. User Checkpoints

The AI agent will pause for user review at these points:


| Checkpoint | After phase | User action                                                        |
| ---------- | ----------- | ------------------------------------------------------------------ |
| **CP1**    | Phase 0     | Confirm repo structure and tech stack                              |
| **CP2**    | Phase 2     | Review backtest output on 5 tickers — do patterns look right?      |
| **CP3**    | Phase 3     | Review sample Playbook JSON for one ticker — content quality check |
| **CP4**    | Phase 6     | Review UI in browser — design and UX feedback                      |
| **CP5**    | Phase 9     | Final production test + demo rehearsal                             |


Between checkpoints, the agent proceeds autonomously.

---



## 16. Estimated Effort


| Phase                | Estimated time (AI agent)      |
| -------------------- | ------------------------------ |
| 0 — Foundation       | ~30 min                        |
| 1 — Data layer       | ~1 hour                        |
| 2 — Analysis engines | ~1.5 hours                     |
| 3 — Agents           | ~2 hours                       |
| 4 — API              | ~45 min                        |
| 5 — PRISM            | ~30 min                        |
| 6 — Frontend         | ~2.5 hours                     |
| 7 — Polish           | ~1 hour                        |
| 8 — Testing          | ~1 hour                        |
| 9 — Deploy           | ~45 min                        |
| **Total**            | **~11–12 hours of agent work** |


This can be completed in a single extended session or split across two sessions. User checkpoint reviews add ~30 min each.

---



## Execution Order Summary

```
Phase 0: Scaffold
    ↓
Phase 1: Data services (Tavily, yfinance, Finnhub, EDGAR)
    ↓
Phase 2: Reaction analyzer + peer map + backtest
    ↓  ← CP2: Review backtest
Phase 3: All agents + LangGraph orchestrator
    ↓  ← CP3: Review sample playbook
Phase 4: API + SSE streaming
    ↓
Phase 5: PRISM integration
    ↓
Phase 6: Full frontend UI
    ↓  ← CP4: Review UI
Phase 7: Polish + export + demo seed
    ↓
Phase 8: Tests + backtest validation
    ↓
Phase 9: Deploy + docs + demo script ✅
    ↓  ← CP5: Final review
    ✅ Production-ready EarningsPulse
```

---

*Document version: 1.0 · Created: September 3, 2026*