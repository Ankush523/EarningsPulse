"""Playbook generation routes — implemented in Phase 4."""

from fastapi import APIRouter

router = APIRouter(prefix="/playbook", tags=["playbook"])

# Endpoints will be added in Phase 4:
# POST /generate
# GET /stream/{job_id}
# GET /{job_id}
