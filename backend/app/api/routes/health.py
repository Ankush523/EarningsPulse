"""Health check routes."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from app.api.deps import get_app_settings
from app.config import Settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(settings: Settings = Depends(get_app_settings)) -> dict:
    """Liveness probe — confirms the API process is running."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/ready")
async def readiness_check(settings: Settings = Depends(get_app_settings)) -> dict:
    """Readiness probe — confirms the API is ready to accept traffic."""
    checks = {
        "api": True,
        "openai_configured": bool(settings.openai_api_key),
        "google_configured": bool(settings.google_api_key),
        "llm_configured": bool(settings.openai_api_key or settings.google_api_key),
        "tavily_configured": bool(settings.tavily_api_key),
        "finnhub_configured": bool(settings.finnhub_api_key),
        "prism_enabled": settings.prism_enabled,
    }
    return {
        "status": "ready",
        "service": settings.app_name,
        "version": settings.app_version,
        "checks": checks,
        "timestamp": datetime.now(UTC).isoformat(),
    }
