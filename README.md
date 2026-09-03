# EarningsPulse

**Know the report. Read the reaction. Watch the ripple.**

AI-powered pre-earnings research agent that generates structured Earnings Playbooks — forecasting report sentiment, modeling price reaction scenarios, and mapping peer spillover.

Built for the [AI x FINANCE HACKATHON – MONEY TALKS](https://luma.com/vljpdtre) (Money Intelligence track).

## Project Structure

```
finance_hackathon/
├── backend/          # FastAPI + LangGraph agents
├── frontend/         # Next.js 14 web app
├── docs/             # Project spec & implementation plan
├── scripts/          # Backtest & demo utilities
└── docker-compose.yml
```

## Prerequisites

- Python 3.12+
- Node.js 20+
- Docker & Docker Compose (optional, recommended)

## Quick Start

### 1. Clone and configure

```bash
cp .env.example .env
# Edit .env with your API keys (not required for Phase 0 health checks)
```

### 2. Run with Docker (recommended)

```bash
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### 3. Run locally (development)

**Backend:**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

## Health Checks

| Service  | Endpoint                    |
|----------|-----------------------------|
| Backend  | `GET http://localhost:8000/health` |
| Backend  | `GET http://localhost:8000/ready`  |
| Frontend | `GET http://localhost:3000/api/health` |

## API Keys (required from Phase 1 onward)

| Key | Purpose | Get it |
|-----|---------|--------|
| `OPENAI_API_KEY` | LLM agents | [platform.openai.com](https://platform.openai.com) |
| `TAVILY_API_KEY` | Live web research | [tavily.com](https://tavily.com) |
| `FINNHUB_API_KEY` | Earnings calendar | [finnhub.io](https://finnhub.io) |
| `PRISM_API_KEY` | Agent observability | Provided at hackathon |

Phase 0 runs without API keys — health checks only.

### Data services (Phase 1)

| Service | Module | API Key |
|---------|--------|---------|
| Price data | `PriceDataService` | None (yfinance) |
| Earnings calendar | `EarningsCalendarService` | `FINNHUB_API_KEY` (yfinance fallback) |
| Web research | `TavilyClient` | `TAVILY_API_KEY` |
| SEC filings | `EdgarClient` | `SEC_USER_AGENT` (email required by SEC) |
| Reaction patterns | `ReactionAnalyzer` | None (uses Phase 1 services) |
| Peer spillover | `PeerMapService` | None (Finnhub improves earnings dates) |

## Testing

```bash
cd backend
pip install -r requirements.txt
pytest
```

### Backtest reaction patterns (Phase 2)

```bash
cd backend && source .venv/bin/activate
python ../scripts/backtest_reactions.py
python ../scripts/backtest_reactions.py --tickers AAPL NVDA TSLA
```

Requires network access and Phase 1 env keys (`FINNHUB_API_KEY` recommended; yfinance fallback works for prices).

### Generate a playbook (Phase 3)

```python
import asyncio
from app.agents import PlaybookOrchestrator

async def main():
    orchestrator = PlaybookOrchestrator()
    playbook = await orchestrator.run("AAPL")
    print(playbook.executive_summary.primary_pattern)
    print(playbook.executive_summary.beat_probability)

asyncio.run(main())
```

Run from `backend/` with venv activated. Requires `OPENAI_API_KEY` for best forecast quality (heuristic fallback works without it).

### REST API (Phase 4)

Start a playbook generation job:

```bash
curl -X POST http://localhost:8000/api/playbook/generate \
  -H "Content-Type: application/json" \
  -d '{"ticker": "AAPL"}'
```

Stream agent progress (SSE):

```bash
curl -N http://localhost:8000/api/playbook/stream/<job_id>
```

Fetch completed playbook:

```bash
curl http://localhost:8000/api/playbook/<job_id>
```

Upcoming earnings calendar:

```bash
curl "http://localhost:8000/api/calendar?days=7"
curl http://localhost:8000/api/calendar/AAPL
```

Interactive docs: http://localhost:8000/docs

Rate limit: 10 playbook generation requests per minute per client IP.

### Trace API (Phase 5)

Fetch the full PRISM-compatible trace for a completed job:

```bash
curl http://localhost:8000/api/trace/<job_id>
```

Trace logs are also persisted locally at `backend/logs/traces/<job_id>.json`.

When `PRISM_API_KEY` and `PRISM_PROJECT_ID` are set, the full agent trajectory is synced to Block Convey PRISM on job completion (local trace always preserved).

## Documentation

- [Project Specification](docs/PROJECT_SPEC.md)
- [Implementation Plan](docs/IMPLEMENTATION_PLAN.md)

## Implementation Phases

| Phase | Status | Description |
|-------|--------|-------------|
| 0 | ✅ | Foundation — scaffold, models, health checks |
| 1 | ✅ | Data layer — Tavily, yfinance, Finnhub, EDGAR |
| 2 | ✅ | Analysis engines — reaction analyzer, peer map |
| 3 | ✅ | Agents — LangGraph orchestrator + 5 agents |
| 4 | ✅ | API — playbook generation + SSE streaming |
| 5 | ✅ | PRISM — observability integration |
| 6 | 🔜 | Frontend — full UI |
| 7 | 🔜 | Polish — export, calendar, demo seed |
| 8 | 🔜 | Testing — E2E, backtest validation |
| 9 | 🔜 | Deploy — production deployment |

## Disclaimer

Not financial advice. For informational and decision-support purposes only.
