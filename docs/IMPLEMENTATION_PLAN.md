# EarningsPulse implementation plan

Build plan for shipping EarningsPulse as a hackathon project. Companion: [PROJECT_SPEC.md](./PROJECT_SPEC.md).

Approach: one Cursor agent ran phases in order with user review at checkpoints.

**Status:** All 10 phases complete (Phases 0–9 merged to `main`; latest Phase 9 PR #9, commit `64016c7`).

**Still before the hackathon:** deploy to Railway + Vercel, run `scripts/verify_deployment.sh`, rehearse [DEMO_SCRIPT.md](./DEMO_SCRIPT.md), tag `v1.0.0`.

## Table of contents

1. [Can this be done solo?](#1-can-this-be-done-solo)
2. [Architecture overview](#2-architecture-overview)
3. [Tech stack decisions](#3-tech-stack-decisions)
4. [Project structure](#4-project-structure)
5. [Environment and dependencies](#5-environment-and-dependencies)
6. [Implementation phases](#6-implementation-phases)
7. [Detailed step-by-step tasks](#7-detailed-step-by-step-tasks)
8. [API and data integration plan](#8-api-and-data-integration-plan)
9. [Agent implementation details](#9-agent-implementation-details)
10. [Frontend implementation details](#10-frontend-implementation-details)
11. [PRISM integration plan](#11-prism-integration-plan)
12. [Testing strategy](#12-testing-strategy)
13. [Production readiness checklist](#13-production-readiness-checklist)
14. [Risks and mitigations](#14-risks-and-mitigations)
15. [User checkpoints](#15-user-checkpoints)
16. [Estimated effort](#16-estimated-effort)

## 1. Can this be done solo?

Yes, with a Cursor coding agent, if the user supplies keys and runs the demo.

| Requirement | Who provides it | Notes |
| ------------------- | -------------------- | --------------------------------------------------------------------- |
| Code implementation | AI agent | Backend, frontend, agents, tests |
| API keys | User | OpenAI/Anthropic, Tavily, Finnhub (free tier), optional PRISM credentials |
| PRISM access | User / hackathon | Block Convey provides at the event; stub locally until then |
| Design decisions | AI agent | Follow the spec; user reviews at checkpoints |
| Deployment | AI agent | Vercel + Railway/Render or all-in-one Docker |
| Demo rehearsal | User | Practice the 3-minute pitch with a live demo |

### What the AI agent handles

- Repository scaffolding and configuration
- Backend services and API routes
- Multi-agent orchestration
- Data pipeline (earnings dates, prices, news, peers)
- Reaction pattern analysis engine
- Spillover correlation engine
- Web UI with live agent trace panel
- PRISM integration (or local stub with swap-in at the hackathon)
- Error handling, retries, fallbacks
- Tests for critical paths
- README, env examples, deployment config
- Demo seed data and backtest scripts

### What the user must provide

- API keys (`.env` file)
- PRISM credentials when available at the hackathon
- Final demo ticker on event day
- 3-minute pitch delivery

### Honest limitations

- Options implied move depends on API availability; falls back to historical-only dip estimation if no key
- PRISM may need same-day integration at the venue if credentials are not available beforehand. A local observability stub keeps the product working either way.
- Analyst estimates quality varies on free-tier APIs; Tavily fills gaps.

## 2. Architecture overview

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

- Frontend sends `POST /api/playbook/generate` with a ticker
- Backend streams agent progress via Server-Sent Events (SSE)
- Final playbook returned as structured JSON
- PRISM events emitted in parallel with the SSE stream

## 3. Tech stack decisions

| Layer | Choice | Rationale |
| ------------------- | ------------------------------------- | ------------------------------------------------------ |
| Frontend | Next.js 16 (App Router) + TypeScript 7 | Turbopack by default, easy Vercel deploy |
| UI | Tailwind CSS + custom glass components | Editorial finance UI without a component library |
| Charts | lightweight-charts | OHLCV reaction workspace (candles, paths, reference lines) |
| Backend | Python 3.12 + FastAPI | Strong ecosystem for finance data and AI agents |
| Agent framework | LangGraph | Multi-agent orchestration with state |
| LLM | OpenAI GPT-4o (primary) | Tool calling and synthesis quality; Anthropic as fallback |
| Web research | Tavily API | Hackathon partner, built for agents |
| Price data | yfinance | Free historical OHLCV |
| Earnings dates | Finnhub free tier | Clean earnings calendar API |
| Filings | SEC EDGAR API | Free, authoritative |
| Cache | In-memory + optional Redis | Avoid redundant API calls during demo |
| Observability | PRISM SDK + local trace store | Hackathon requirement |
| Testing | pytest (backend) + Playwright (E2E) | Critical path coverage |
| Deploy | Vercel (frontend) + Railway (backend) | Free tiers, quick setup |

## 4. Project structure

```
EarningsPulse/
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
│   │   │   ├── RunPanel.tsx           # PRISM live trace (dark surface)
│   │   │   ├── PlaybookView.tsx
│   │   │   ├── ScenarioTree.tsx
│   │   │   ├── reaction/
│   │   │   │   ├── ReactionWorkspace.tsx
│   │   │   │   ├── ReactionCandleChart.tsx
│   │   │   │   └── ReactionMoveHistogram.tsx
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

## 5. Environment and dependencies

### Required environment variables

```bash
# LLM
OPENAI_API_KEY=sk-...

# Hackathon partners
TAVILY_API_KEY=tvly-...

# Market data
FINNHUB_API_KEY=...          # Free tier: 60 calls/min

# PRISM (Block Convey). Add at hackathon if not available earlier.
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

## 6. Implementation phases

| Phase | Name | Deliverable | Dependency | Status |
| ----- | ---------------- | ------------------------------------------------- | ---------- | ------ |
| 0 | Foundation | Repo scaffold, Docker, env, health checks | None | Done |
| 1 | Data layer | Price, earnings, news, EDGAR services working | Phase 0 | Done |
| 2 | Analysis engines | Reaction analyzer + peer map + pattern classifier | Phase 1 | Done |
| 3 | Agents | All 5 agents + orchestrator via LangGraph | Phase 2 | Done |
| 4 | API | REST + SSE streaming endpoints | Phase 3 | Done |
| 5 | PRISM | Observability integration + trace panel data | Phase 4 | Done |
| 6 | Frontend | Full UI: input, trace, playbook viewer | Phase 4, 5 | Done |
| 7 | Polish | Export, calendar, error states, loading UX | Phase 6 | Done |
| 8 | Testing | Unit, integration, E2E, backtest validation | Phase 7 | Done |
| 9 | Deploy | Production configs, docs, demo script | Phase 8 | Done |

Phases are sequential. All phases merged to `main` as of September 3, 2026.

## 7. Detailed step-by-step tasks

### Phase 0. Foundation

- [x] Initialize monorepo with `backend/` and `frontend/` directories
- [x] Set up Python virtual environment, `requirements.txt` (FastAPI, LangGraph, yfinance, httpx, pydantic, etc.)
- [x] Set up Next.js 16 with TypeScript 7, Tailwind, custom glass UI
- [x] Create `.env.example` with all required keys documented
- [x] Create `docker-compose.yml` for local dev (backend + frontend)
- [x] Implement health check endpoints (`GET /health` on backend, frontend loads)
- [x] Write initial `README.md` with setup instructions
- [x] Define all Pydantic models for Playbook, AgentState, TraceEvent

**Exit criteria:** `docker-compose up` runs both services; health checks pass.

### Phase 1. Data layer

- [x] `price_data.py`: yfinance wrapper
  - Fetch OHLCV for date range
  - Fetch price around earnings dates (±3 days window)
  - Calculate returns, dips, recovery metrics
- [x] `earnings_calendar.py`: Finnhub wrapper
  - Upcoming earnings for next 7 days
  - Historical earnings dates for a ticker (last 8 events)
- [x] `tavily_client.py`: Tavily search wrapper
  - Search company news (last 90 days)
  - Search earnings-related content
  - Extract and summarize results
- [x] `edgar_client.py`: SEC EDGAR wrapper
  - Fetch latest 10-Q/10-K filing metadata
  - Link to previous earnings report
- [x] `cache.py`: In-memory TTL cache for API responses
- [x] Unit tests for each service with mocked responses

**Exit criteria:** Given a ticker (for example AAPL), all services return valid data independently.

### Phase 2. Analysis engines

- [x] `reaction_analyzer.py`: Core pattern engine
  - Input: list of (earnings_date, prices around date)
  - Output per event: direction, dip %, recovery %, time-to-bottom
  - Aggregate: archetype classification, avg dip, avg recovery, pattern frequency
  - Classify into archetypes (Dip-Then-Rally, Immediate Rip, etc.)
- [x] `peer_map.py`: Spillover engine
  - Static sector taxonomy (GICS-based peer groups for major sectors)
  - Dynamic correlation: compute return correlation on past earnings dates
  - Output: ranked peer list with correlation scores and relationship types
- [x] `confidence.py`: Confidence scoring utility
  - Score based on data availability, sample size, source quality
- [x] `scripts/backtest_reactions.py`: Validation script
  - Run reaction analyzer on 5 well-known tickers
  - Print pattern classifications for manual verification
- [x] Unit tests with synthetic price data (known dip-then-rally pattern)

**Exit criteria:** Backtest script correctly identifies known patterns on AAPL, NVDA, TSLA historical earnings.

### Phase 3. Agents

- [x] `agent_state.py`: Shared LangGraph state schema
- [x] `research.py`: Research Agent
  - Tools: Tavily search, EDGAR fetch, earnings calendar
  - Output: structured research bundle (news, last ER summary, key developments)
- [x] `forecast.py`: Forecast Agent
  - Input: research bundle
  - Output: beat/miss/inline probabilities, key metrics, bull/bear cases
- [x] `reaction.py`: Reaction Agent
  - Tools: price_data, reaction_analyzer
  - Output: historical pattern stats, archetype, scenario probabilities
- [x] `spillover.py`: Spillover Agent
  - Tools: peer_map, Tavily (peer context), price_data (correlation)
  - Output: ranked peer list with correlation and direction bias
- [x] `synthesis.py`: Synthesis Agent
  - Input: all agent outputs
  - Output: complete Playbook JSON matching spec schema
  - Conflict resolution, confidence assignment, source linking
- [x] `orchestrator.py`: LangGraph workflow
  - Parallel: Research + Reaction
  - Sequential: Forecast (needs Research) → Spillover (needs Forecast) → Synthesis
  - Error handling: retry failed tools, fallback sources
  - Emit trace events at each step
- [x] Integration test: end-to-end agent run for one ticker

**Exit criteria:** `orchestrator.run("AAPL")` returns a complete Playbook JSON.

### Phase 4. API layer

- [x] `POST /api/playbook/generate`: Start playbook generation
  - Input: `{ ticker: string }`
  - Returns: `{ job_id: string }`
- [x] `GET /api/playbook/stream/{job_id}`: SSE stream
  - Events: `agent_start`, `tool_call`, `agent_complete`, `playbook_ready`, `error`
  - Each event includes PRISM-compatible trace data
- [x] `GET /api/playbook/{job_id}`: Fetch completed playbook
- [x] `GET /api/calendar`: Upcoming earnings (next 7 days)
- [x] `GET /api/calendar/{ticker}`: Earnings date for specific ticker
- [x] Request validation, error responses, rate limiting (basic)
- [x] CORS configuration for frontend

**Exit criteria:** API endpoints work via curl/Postman; SSE stream emits events during generation.

### Phase 5. PRISM integration

- [x] `prism_client.py`: PRISM SDK wrapper
  - If PRISM credentials available: send traces to Block Convey
  - If not: write traces to local JSON log (swap-in ready)
- [x] Emit PRISM events from orchestrator at every state transition:
  - Agent started/completed
  - Tool call initiated/completed/failed
  - Confidence updated
  - Error + retry
  - Final playbook generated
- [x] Trace schema matches PRISM expected format (or documented local format)
- [x] `GET /api/trace/{job_id}`: Full trace for a playbook generation job

**Exit criteria:** Agent run produces a complete trace log viewable via API; PRISM-compatible format.

### Phase 6. Frontend

- [x] Landing page (`page.tsx`):
  - Hero with tagline and brief explanation
  - Ticker input with search/autocomplete
  - Generate Playbook CTA
  - Upcoming earnings calendar preview
- [x] `usePlaybookStream.ts`: SSE hook
  - Connect to stream endpoint
  - Parse events, update state
  - Handle completion and errors
- [x] `RunPanel.tsx`: Live PRISM trace viewer
  - Step-by-step agent progress
  - Tool call log with timestamps
  - Status indicators (running/complete/error)
  - Expandable detail per step
- [x] `PlaybookView.tsx`: Main output display
  - Section A: Executive summary
  - Section B: Report forecast
  - Section C: Reaction workspace + scenario tree (interactive)
  - Section D: Peer spillover table
  - Section E: Action playbook
  - Section F: Sources list
- [x] `ReactionWorkspace.tsx`: Price reaction chart workspace
  - Daily OHLCV candles via lightweight-charts
  - Historical earnings path overlays, median path, pivot/support/resistance lines
  - Move histogram and overlay toggles
  - Theme-aware chart palette (light / dark)
- [x] `ScenarioTree.tsx`: Interactive scenario tree with probabilities
- [x] `PeerSpilloverTable.tsx`: Sortable peer table with correlation bars
- [x] `ConfidenceBadge.tsx`: Reusable confidence tier badge
- [x] `calendar/page.tsx`: Full earnings calendar view
- [x] Responsive design, loading/error/empty states
- [x] Disclaimer banner (persistent)

**Exit criteria:** Full user flow works in browser: input ticker → watch agent run → view playbook.

### Phase 7. Polish

- [x] PDF export of playbook (backend generation or frontend print)
- [x] JSON export download button
- [x] Pre-cache demo ticker via `scripts/seed_demo.py`
- [x] Loading skeletons and transitions
- [x] Error recovery UX (retry button, partial results)
- [x] SEO meta tags and favicon
- [x] Performance: playbook generation under 2 minutes
- [x] Mobile-responsive layout verification
- [x] Wide playbook layout (`max-w-page` shell, full-width section grids)
- [x] Reaction chart workspace: backend `reaction_chart.py` payload + frontend lightweight-charts UI

**Exit criteria:** Demo-ready UX on happy path and error path.

### Phase 8. Testing

- [x] Unit tests: reaction_analyzer, peer_map, confidence scoring
- [x] Agent tests: each agent with mocked tools
- [x] Integration test: full orchestrator run with mocked external APIs
- [x] API tests: all endpoints, SSE stream format
- [x] E2E test (Playwright): input ticker → wait for playbook → verify sections render
- [x] Backtest validation: run on 5 tickers, verify pattern labels are reasonable
- [x] Fix any failures

**Exit criteria:** All tests pass; backtest output reviewed and sensible.

### Phase 9. Deploy and document

**Merged:** PR #9 → `main` (`64016c7`)

#### Code deliverables (complete)

- [x] Deployment configs: Railway (`backend/railway.toml`), Render (`render.yaml`), Vercel (`frontend/vercel.json`), Docker production hardening
- [x] Production env vars documented (`.env.example`, `docs/DEPLOYMENT.md`)
- [x] CORS auto-includes `FRONTEND_URL` for production domains
- [x] `scripts/verify_deployment.sh`: post-deploy health + demo verification
- [x] Final README: overview, architecture, API reference, deployment, demo
- [x] `docs/DEMO_SCRIPT.md`: 3-minute pitch outline
- [x] `docs/DEPLOYMENT.md`: Railway/Render + Vercel step-by-step guide

#### Post-merge checklist (user, before hackathon)

- [ ] Deploy backend to Railway (or Render). See [DEPLOYMENT.md](./DEPLOYMENT.md).
- [ ] Deploy frontend to Vercel; set `NEXT_PUBLIC_BACKEND_URL`
- [ ] Set `FRONTEND_URL` on backend to Vercel domain; redeploy backend
- [ ] Run `./scripts/verify_deployment.sh <api-url> <vercel-url>`
- [ ] Rehearse demo 3× using [DEMO_SCRIPT.md](./DEMO_SCRIPT.md)
- [ ] Tag release `v1.0.0` after production verified

**Exit criteria:** README and demo script complete. Production URL live (user deploy). Demo rehearsed.

## 8. API and data integration plan

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

## 9. Agent implementation details

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

| Agent | Tools |
| --------- | ---------------------------------------------------------- |
| Research | `tavily_search`, `fetch_edgar_filing`, `get_earnings_date` |
| Forecast | (no external tools; LLM reasoning on research bundle) |
| Reaction | `fetch_price_history`, `analyze_earnings_reactions` |
| Spillover | `get_peer_map`, `compute_correlation`, `tavily_search` |
| Synthesis | (no external tools; LLM synthesis of all outputs) |

### Retry policy

- Tool call fails → retry once with backoff
- Second failure → use fallback source if available
- No fallback → mark section as `low confidence` and continue
- Never block the entire playbook for one failed data point

## 10. Frontend implementation details

### Key user flows

**Flow 1. Generate Playbook**

1. User lands on homepage
2. Types ticker (for example "MRVL") or picks from calendar
3. Clicks Generate Playbook
4. Redirected to `/playbook/{job_id}`
5. Agent trace panel shows live progress (SSE)
6. Playbook sections populate as agents complete
7. Full playbook rendered when synthesis finishes

**Flow 2. Browse calendar**

1. User navigates to `/calendar`
2. Sees upcoming earnings for the week
3. Clicks any ticker → starts Flow 1

### Design system

| Element | Style |
| ----------------- | ------------------------------------------ |
| Page shell | `max-w-page` (`85rem` / 1360px), aligned header + footer |
| Background | Light stone paper (`#eef2fb`) or dark navy (`#0b0f16`) via `ThemeProvider` |
| Ink | Navy / white tokens (`--ink`, `--ink-soft`), soft ink for secondary text |
| Direction colour | Up / down / caution tokens only |
| Surfaces | Glass panels (`glass-panel`, `glass-panel-strong`) with blur and rim shadows |
| Agent run panel | Dark surface (`RunPanel.tsx`) — always dark even in light mode |
| Typography | System UI sans stack + IBM Plex Mono (figures, tickers) |
| Prose measure | `max-w-measure` (`42rem`) for marketing copy and disclaimers only |
| Playbook layout | Section titles stack until `xl`; sticky title rail + full-width content grids at `xl+` |
| Charts | lightweight-charts (reaction workspace candles, paths, reference lines) |

## 11. PRISM integration plan

### Local stub (build now)

If PRISM credentials are not available before the hackathon:

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
- Frontend `RunPanel` reads from the same SSE stream
- At the hackathon: add `PRISM_API_KEY` to env → auto-switches to live PRISM

### PRISM event types

| Event | Payload |
| --------------------- | -------------------------------------- |
| `run_started` | ticker, timestamp |
| `agent_started` | agent_name |
| `tool_call_started` | tool_name, input_summary |
| `tool_call_completed` | tool_name, output_summary, latency_ms |
| `tool_call_failed` | tool_name, error, retry_attempt |
| `agent_completed` | agent_name, output_summary, confidence |
| `confidence_updated` | section, old_score, new_score, reason |
| `run_completed` | total_latency_ms, playbook_id |
| `run_failed` | error, partial_results |

## 12. Testing strategy

**Status (Phase 8):** Implemented. See `backend/tests/`, `frontend/e2e/`, `.github/workflows/ci.yml`, and `scripts/run_tests.sh`.

| Level | What | How | Status |
| --------------- | --------------------------------------- | -------------------------------------- | ------ |
| Unit | Reaction analyzer, peer map, confidence | pytest with synthetic data | Done |
| Unit | Individual agent logic | pytest with mocked LLM + tools | Done |
| Integration | Full orchestrator | pytest with mocked external APIs | Done |
| API | All endpoints + SSE format | pytest + httpx AsyncClient | Done |
| E2E | Full user flow | Playwright: demo AAPL → playbook sections | Done |
| Validation | Pattern accuracy | Backtest tests on 5 tickers (mocked) | Done |
| Manual | Demo reliability | 3 consecutive live runs on demo ticker | User (post-deploy) |

### Backtest tickers (validation, not hardcoded logic)

- AAPL (mega-cap, well-documented reactions)
- NVDA (high volatility, dip-then-rally candidate)
- TSLA (volatile, mixed patterns)
- JPM (financials sector baseline)
- AMZN (inline/mixed pattern candidate)

## 13. Production readiness checklist

**Codebase:** complete (all phases merged to `main`).  
**Go-live:** follow [DEPLOYMENT.md](./DEPLOYMENT.md) and the Phase 9 post-merge checklist below.

### Functionality

- [x] Playbook generates for any valid US equity ticker
- [x] All 6 playbook sections populated with real data
- [x] Agent trace visible in real time
- [x] Earnings calendar loads upcoming week
- [x] PDF/JSON export works
- [x] Error states handled gracefully (invalid ticker, API down, partial data)

### Quality

- [x] All tests pass
- [x] No hardcoded ticker-specific logic
- [x] Every factual claim has a source link
- [x] Confidence tiers assigned correctly
- [x] Disclaimer visible on all pages
- [x] Generation completes in under 2 minutes

### Deployment

- [ ] Backend deployed and healthy. See [DEPLOYMENT.md](./DEPLOYMENT.md).
- [ ] Frontend deployed and connected to backend
- [x] Environment variables documented
- [x] CORS configured correctly (`FRONTEND_URL` auto-merge)
- [ ] HTTPS enabled on live URLs (automatic via Vercel + Railway/Render)

### Demo

- [x] Demo script written (`docs/DEMO_SCRIPT.md`)
- [ ] Demo ticker pre-tested 3+ times on production URL
- [x] PRISM trace visible and narratable
- [x] Fallback plan if live APIs fail during demo (cached playbook: Demo AAPL)

### Documentation

- [x] README with setup and architecture
- [x] PROJECT_SPEC.md
- [x] IMPLEMENTATION_PLAN.md
- [x] DEMO_SCRIPT.md
- [x] DEPLOYMENT.md
- [x] .env.example with all keys documented

## 14. Risks and mitigations

| Risk | Impact | Mitigation |
| --------------------------------- | ------------------------- | --------------------------------------------------------------------- |
| Tavily API rate limit during demo | Research agent fails | Pre-cache demo ticker; TTL cache |
| Finnhub free tier limits | Calendar fails | yfinance fallback for earnings dates |
| LLM hallucinates metrics | Bad playbook data | Source-required policy in synthesis agent; confidence tiers |
| PRISM credentials unavailable | No live PRISM integration | Local stub with identical trace format; swap at venue |
| yfinance rate limiting | Price data fails | Cache aggressively; Alpha Vantage fallback |
| Agent takes over 2 min | Bad demo experience | Parallel agent execution; cache; pre-warm demo ticker |
| Obscure ticker has no data | Empty playbook sections | Graceful degradation; flag low confidence; suggest similar ticker |
| Hackathon WiFi issues | APIs unreachable | Offline demo mode with cached playbook JSON |

## 15. User checkpoints

The AI agent pauses for user review at these points:

| Checkpoint | After phase | User action |
| ---------- | ----------- | ------------------------------------------------------------------ |
| CP1 | Phase 0 | Confirm repo structure and tech stack |
| CP2 | Phase 2 | Review backtest output on 5 tickers. Do patterns look right? |
| CP3 | Phase 3 | Review sample Playbook JSON for one ticker. Content quality check. |
| CP4 | Phase 6 | Review UI in browser. Design and UX feedback. |
| CP5 | Phase 9 | Deploy to production, verify, rehearse demo, tag `v1.0.0` |

Between checkpoints, the agent proceeds on its own.

## 16. Estimated effort

| Phase | Estimated time (AI agent) |
| -------------------- | ------------------------------ |
| 0. Foundation | ~30 min |
| 1. Data layer | ~1 hour |
| 2. Analysis engines | ~1.5 hours |
| 3. Agents | ~2 hours |
| 4. API | ~45 min |
| 5. PRISM | ~30 min |
| 6. Frontend | ~2.5 hours |
| 7. Polish | ~1 hour |
| 8. Testing | ~1 hour |
| 9. Deploy | ~45 min |
| Total | ~11–12 hours of agent work |

This can finish in one long session or two shorter ones. User checkpoint reviews add about 30 minutes each.

## Execution order summary

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
Phase 9: Deploy + docs + demo script (merged PR #9)
    ↓  ← CP5: Deploy + demo rehearsal (user)
    Code-complete EarningsPulse, ready for hackathon
```

---

Document version 1.3. Created September 3, 2026. Updated September 4, 2026 (reaction workspace, layout tokens, design system refresh).
