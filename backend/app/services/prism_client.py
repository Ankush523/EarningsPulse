"""PRISM (Block Convey) observability client with local fallback."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.config import Settings, get_settings
from app.models.trace import TraceEvent, TraceLog
from app.services.trace_store import trace_event_to_prism_step

logger = logging.getLogger(__name__)

PRISM_TRAJECTORY_PATH = "/api/trajectories"
PRISM_TRACE_PATH = "/api/traces"


class PrismClient:
    """
    Forward agent traces to Block Convey PRISM when credentials are configured.

    Without credentials, operates in local-only mode: traces are stored in the
    job store and persisted as JSON via TraceStore.
    """

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()
        self._local_mode = not self._settings.prism_enabled
        self._http: httpx.AsyncClient | None = None
        self._sdk: Any | None = None
        self._buffers: dict[str, list[TraceEvent]] = {}
        self._lock = asyncio.Lock()

        if not self._local_mode:
            self._init_sdk()

    @property
    def local_mode(self) -> bool:
        return self._local_mode

    @property
    def enabled(self) -> bool:
        return self._settings.prism_enabled

    def _init_sdk(self) -> None:
        try:
            from prismtrace import PRISMtrace

            api_key = self._settings.prism_api_key
            project_id = self._settings.prism_project_id
            if not api_key or not project_id:
                self._local_mode = True
                return

            self._sdk = PRISMtrace(
                api_key=api_key,
                project_id=project_id,
                host=self._settings.prism_host,
            )
            logger.info("PRISM SDK initialized (host=%s)", self._settings.prism_host)
        except ImportError:
            logger.info("prismtrace-sdk not installed — using REST fallback for PRISM sync")
        except Exception as exc:
            logger.warning("PRISM SDK initialization failed: %s", exc)
            self._local_mode = True

    async def emit(self, event: TraceEvent | dict[str, Any]) -> None:
        """Buffer a trace event for batch sync to PRISM."""
        if isinstance(event, TraceEvent):
            trace_event = event
        else:
            trace_event = TraceEvent.model_validate(event)

        if self._local_mode:
            return

        async with self._lock:
            self._buffers.setdefault(trace_event.job_id, []).append(trace_event)

    async def sync_trace_log(self, trace_log: TraceLog) -> bool:
        """
        Submit a complete trace log to PRISM and mark sync status.

        Returns True when remote sync succeeds, False in local mode or on failure.
        """
        if self._local_mode:
            return False

        steps = [trace_event_to_prism_step(event) for event in trace_log.events]
        if not steps:
            logger.debug("No trace events to sync for job %s", trace_log.job_id)
            return False

        try:
            if self._sdk is not None:
                synced = await asyncio.to_thread(
                    self._submit_trajectory_sdk,
                    trace_log,
                    steps,
                )
            else:
                synced = await self._submit_trajectory_rest(trace_log, steps)

            if synced:
                await self._submit_summary_trace(trace_log, steps)

            async with self._lock:
                self._buffers.pop(trace_log.job_id, None)

            if synced:
                logger.info("PRISM sync completed for job %s", trace_log.job_id)
            return synced
        except Exception as exc:
            logger.warning(
                "PRISM sync failed for job %s (local trace preserved): %s",
                trace_log.job_id,
                exc,
            )
            return False

    def _submit_trajectory_sdk(
        self,
        trace_log: TraceLog,
        steps: list[dict[str, Any]],
    ) -> bool:
        assert self._sdk is not None
        final_status = "success"
        if steps and steps[-1].get("step_type") == "error":
            final_status = "error"

        agent_name = f"earningspulse-{trace_log.ticker.lower()}"
        result = self._sdk.submit_trajectory(
            steps,
            agent_name=agent_name,
            agent_id=agent_name,
            model=self._settings.llm_model,
            request_id=trace_log.job_id,
            conversation_id=trace_log.job_id,
            final_status=final_status,
            async_send=False,
        )
        self._sdk.flush()
        return result is not None

    async def _submit_trajectory_rest(
        self,
        trace_log: TraceLog,
        steps: list[dict[str, Any]],
    ) -> bool:
        client = await self._get_http_client()
        url = f"{self._settings.prism_host.rstrip('/')}{PRISM_TRAJECTORY_PATH}"
        agent_name = f"earningspulse-{trace_log.ticker.lower()}"
        final_status = "error" if steps and steps[-1].get("step_type") == "error" else "success"
        payload = {
            "project_id": self._settings.prism_project_id,
            "conversation_id": trace_log.job_id,
            "request_id": trace_log.job_id,
            "agent_id": agent_name,
            "agent_name": agent_name,
            "model": self._settings.llm_model,
            "steps": steps,
            "total_duration_ms": trace_log.total_latency_ms
            or sum(step.get("duration_ms") or 0 for step in steps),
            "final_status": final_status,
            "metadata": {
                "job_id": trace_log.job_id,
                "ticker": trace_log.ticker,
                "total_latency_ms": trace_log.total_latency_ms,
                "source": "earningspulse",
            },
        }
        headers = {
            "x-prismtrace-key": self._settings.prism_api_key or "",
            "Content-Type": "application/json",
        }
        response = await client.post(url, json=payload, headers=headers, timeout=30.0)
        if response.status_code >= 400:
            raise RuntimeError(f"PRISM API returned {response.status_code}: {response.text[:500]}")
        return True

    async def _submit_summary_trace(
        self,
        trace_log: TraceLog,
        steps: list[dict[str, Any]],
    ) -> None:
        """Send one summary trace so the PRISM dashboard live counter updates."""
        agent_name = f"earningspulse-{trace_log.ticker.lower()}"
        tool_calls = sum(1 for step in steps if step.get("step_type") == "tool_call")
        final_step = steps[-1].get("label", "Playbook generation completed")
        payload = {
            "project_id": self._settings.prism_project_id,
            "model": self._settings.llm_model,
            "input_messages": [
                {
                    "role": "user",
                    "content": f"Generate earnings playbook for {trace_log.ticker}",
                }
            ],
            "output_message": final_step,
            "latency_ms": trace_log.total_latency_ms or 0,
            "agent_name": agent_name,
            "agent_id": agent_name,
            "trace_id": trace_log.job_id,
            "metadata": {
                "job_id": trace_log.job_id,
                "ticker": trace_log.ticker,
                "source": "earningspulse",
                "tool_calls": tool_calls,
                "step_count": len(steps),
            },
        }
        headers = {
            "x-prismtrace-key": self._settings.prism_api_key or "",
            "Content-Type": "application/json",
        }
        try:
            if self._sdk is not None:
                await asyncio.to_thread(self._submit_summary_trace_sdk, trace_log, steps)
            else:
                client = await self._get_http_client()
                url = f"{self._settings.prism_host.rstrip('/')}{PRISM_TRACE_PATH}"
                response = await client.post(url, json=payload, headers=headers, timeout=30.0)
                if response.status_code >= 400:
                    logger.warning(
                        "PRISM summary trace failed for job %s: %s",
                        trace_log.job_id,
                        response.text[:200],
                    )
        except Exception as exc:
            logger.warning(
                "PRISM summary trace failed for job %s: %s",
                trace_log.job_id,
                exc,
            )

    def _submit_summary_trace_sdk(
        self,
        trace_log: TraceLog,
        steps: list[dict[str, Any]],
    ) -> None:
        assert self._sdk is not None
        agent_name = f"earningspulse-{trace_log.ticker.lower()}"
        tool_calls = sum(1 for step in steps if step.get("step_type") == "tool_call")
        final_step = steps[-1].get("label", "Playbook generation completed")
        self._sdk.trace_llm(
            model=self._settings.llm_model,
            input_messages=[
                {
                    "role": "user",
                    "content": f"Generate earnings playbook for {trace_log.ticker}",
                }
            ],
            output=final_step,
            latency_ms=trace_log.total_latency_ms or 0,
            trace_id=trace_log.job_id,
            agent_id=agent_name,
            agent_name=agent_name,
            metadata={
                "job_id": trace_log.job_id,
                "ticker": trace_log.ticker,
                "source": "earningspulse",
                "tool_calls": tool_calls,
                "step_count": len(steps),
            },
        )
        self._sdk.flush()

    async def _get_http_client(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient()
        return self._http

    async def close(self) -> None:
        if self._http is not None and not self._http.is_closed:
            await self._http.aclose()


# Application-wide singleton
_prism_client: PrismClient | None = None


def get_prism_client() -> PrismClient:
    global _prism_client
    if _prism_client is None:
        _prism_client = PrismClient()
    return _prism_client
