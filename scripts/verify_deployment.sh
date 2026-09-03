#!/usr/bin/env bash
# Verify a deployed (or local) EarningsPulse stack is healthy and demo-ready.
set -euo pipefail

BACKEND_URL="${1:-${BACKEND_URL:-http://localhost:8000}}"
FRONTEND_URL="${2:-${FRONTEND_URL:-http://localhost:3000}}"

BACKEND_URL="${BACKEND_URL%/}"
FRONTEND_URL="${FRONTEND_URL%/}"

echo "==> Backend health: $BACKEND_URL/health"
curl -fsS "$BACKEND_URL/health" | head -c 200
echo

echo "==> Backend ready:  $BACKEND_URL/ready"
curl -fsS "$BACKEND_URL/ready" | head -c 400
echo

echo "==> Frontend health: $FRONTEND_URL/api/health"
curl -fsS "$FRONTEND_URL/api/health" | head -c 200
echo

echo "==> Demo AAPL instant playbook"
demo_response="$(curl -fsS -X POST "$BACKEND_URL/api/playbook/demo/AAPL")"
echo "$demo_response" | head -c 300
echo

if ! echo "$demo_response" | grep -q '"job_id":"demo_aapl"'; then
  echo "ERROR: Demo AAPL did not return demo_aapl job_id" >&2
  exit 1
fi

echo "==> Deployment verification passed"
