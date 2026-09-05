# EarningsPulse frontend

Next.js 16 (App Router) web UI for playbook generation, live agent traces, and the earnings playbook viewer.

## Getting started

```bash
bun install
bun run dev
```

Open [http://localhost:3000](http://localhost:3000). The backend API defaults to `http://localhost:8000` via `NEXT_PUBLIC_BACKEND_URL`.

## Scripts

| Command | Purpose |
|---------|---------|
| `bun run dev` | Development server (Turbopack) |
| `bun run build` | Production build |
| `bun run lint` | oxlint |
| `bun run typecheck` | TypeScript (`tsc --noEmit`) |
| `bun run knip` | Unused files, deps, exports |
| `bun run doctor` | React Doctor health scan |
| `bun run test:e2e` | Playwright (starts backend + frontend) |

## Layout and design tokens

Defined in `tailwind.config.ts` and `src/app/globals.css`:

| Token | Value | Use |
|-------|-------|-----|
| `max-w-page` | `85rem` (1360px) | Header, footer, home, calendar, playbook shell |
| `max-w-measure` | `42rem` | Long-form prose on marketing pages and disclaimers |
| `--up` / `--down` / `--caution` | CSS variables | Direction-only colour (beat/miss, charts, badges) |

Playbook pages use a wide data-workspace layout: section cards fill the page shell; titles stack above content until `xl`, then sit in a sticky left rail. Internal grids (odds strip, forecast cases, reaction stats) expand to the full content column — no nested `max-w-measure` inside panels.

## Key components

| Area | Files |
|------|-------|
| Playbook viewer | `PlaybookView.tsx`, `playbook/PlaybookSection.tsx`, `PlaybookPageClient.tsx` |
| Reaction workspace | `reaction/ReactionWorkspace.tsx`, `ReactionCandleChart.tsx`, `ReactionMoveHistogram.tsx` |
| Agent trace | `RunPanel.tsx` (dark surface) |
| Theme | `ThemeProvider.tsx`, `ThemeToggle.tsx`, `lib/theme.ts` |
| Charts | [lightweight-charts](https://tradingview.github.io/lightweight-charts/) v5 |

Typography: system UI sans stack in `globals.css`; IBM Plex Mono via `next/font` for tickers and figures.

## Docs

Monorepo docs live in `../docs/` — see [IMPLEMENTATION_PLAN.md](../docs/IMPLEMENTATION_PLAN.md) §10 for frontend flows and the design system.
