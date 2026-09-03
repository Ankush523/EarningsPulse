"""API dependencies."""

from functools import lru_cache

from app.agents.orchestrator import PlaybookOrchestrator
from app.config import Settings, get_settings
from app.services.earnings_calendar import EarningsCalendarService
from app.services.job_store import JobStore, job_store
from app.services.playbook_runner import PlaybookJobRunner
from app.services.prism_client import PrismClient, get_prism_client
from app.services.trace_store import TraceStore


def get_app_settings() -> Settings:
    return get_settings()


@lru_cache
def get_orchestrator() -> PlaybookOrchestrator:
    return PlaybookOrchestrator(settings=get_settings())


def get_job_store() -> JobStore:
    return job_store


def get_job_runner() -> PlaybookJobRunner:
    return PlaybookJobRunner(
        store=job_store,
        orchestrator=get_orchestrator(),
        settings=get_settings(),
        prism_client=get_prism_client(),
        trace_store=get_trace_store(),
    )


def get_trace_store() -> TraceStore:
    return TraceStore(store=job_store, settings=get_settings())


def get_prism_client_dep() -> PrismClient:
    return get_prism_client()


def get_earnings_service() -> EarningsCalendarService:
    return EarningsCalendarService(settings=get_settings())
