#!/usr/bin/env bash
# Run all EarningsPulse test suites (backend, frontend property/build, and E2E).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Backend lint (ruff)"
cd backend
uv run --frozen ruff check app tests
uv run --frozen ruff format --check app tests

echo "==> Backend type check (ty)"
uv run --frozen ty check

echo "==> Backend tests (pytest)"
uv run --frozen python -m pytest tests/ -q
cd "$ROOT"

echo "==> Frontend property tests (Hegel)"
cd frontend
bun run test:property

echo "==> Frontend lint (oxlint)"
bun run lint

echo "==> Frontend unused code (knip)"
bun run knip

echo "==> Frontend typecheck"
bun run typecheck

echo "==> Frontend production build"
bun run build
cd "$ROOT"

if [[ "${SKIP_E2E:-}" == "1" ]]; then
  echo "==> Skipping E2E (SKIP_E2E=1)"
  exit 0
fi

echo "==> Frontend E2E (Playwright)"
cd frontend
if [[ "${CI:-}" == "true" ]]; then
  bunx playwright install --with-deps chromium
fi
bun run test:e2e
cd "$ROOT"

echo "==> All tests passed"
