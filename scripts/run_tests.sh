#!/usr/bin/env bash
# Run all EarningsPulse test suites (backend unit/integration + frontend build + E2E).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Backend tests (pytest)"
cd backend
if [[ -d .venv ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi
python -m pytest tests/ -q
cd "$ROOT"

echo "==> Frontend production build"
cd frontend
npm run build
cd "$ROOT"

if [[ "${SKIP_E2E:-}" == "1" ]]; then
  echo "==> Skipping E2E (SKIP_E2E=1)"
  exit 0
fi

echo "==> Frontend E2E (Playwright)"
cd frontend
if [[ "${CI:-}" == "true" ]]; then
  npx playwright install --with-deps chromium
fi
npm run test:e2e
cd "$ROOT"

echo "==> All tests passed"
