## Learned User Preferences

- After finishing a change, create a GitHub PR and merge it to main without waiting for review.
- Use Bun (`bun` / `bunx`) for frontend package installs and CLIs, not npm or npx.
- After landing work on GitHub, close solved issues and delete leftover merged branches.
- Prefer targeted dead-code removal over a broad slop pass unless asked to go further.
- Keep React Compiler enabled in the Next.js frontend.

## Learned Workspace Facts

- Monorepo: FastAPI backend (Python 3.12, uv, ruff, ty, pytest) and Next.js 16 frontend (Bun 1.4, React 19, TypeScript 7, oxlint).
- `origin` is Cursor-hosted; GitHub PRs for this checkout go to `gpu004/EarningsPulse` (original repo: `Ankush523/EarningsPulse`).
- Playbook live progress is SSE (`EventSource`, `GET /api/playbook/stream/{job_id}`), not WebSockets.
- React Compiler is on via `babel-plugin-react-compiler` and `reactCompiler: true` in `frontend/next.config.ts`.
- CI wraps `uv sync` and `bun install` with Socket Firewall Free (`sfw`) in firewall-free mode (no Socket account).
- React Doctor runs as `bun run doctor` from `frontend/`; `.github/workflows/react-doctor.yml` scans `frontend/` on PRs (advisory).
- Frontend lint is oxlint; ESLint / eslint-config-next were removed.
- Playwright e2e starts the API with system `python -m uvicorn`, not the uv venv, which can fail CI even when backend/frontend jobs pass.
- Root `AGENTS.md` is agent memory; `frontend/AGENTS.md` is Next.js-generated agent rules and should not be treated as memory.
