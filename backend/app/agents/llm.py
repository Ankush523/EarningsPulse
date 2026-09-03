"""LLM client with structured JSON output and deterministic fallback."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Thin wrapper around OpenAI chat completions for agent reasoning."""

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

    @property
    def enabled(self) -> bool:
        return bool(self._settings.openai_api_key)

    async def invoke_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        fallback: dict[str, Any],
    ) -> dict[str, Any]:
        """Return parsed JSON from the LLM, or fallback when unavailable."""
        if not self.enabled:
            logger.info("LLM disabled — using deterministic fallback")
            return fallback

        try:
            from langchain_openai import ChatOpenAI
            from langchain_core.messages import HumanMessage, SystemMessage

            llm = ChatOpenAI(
                model=self._settings.llm_model,
                api_key=self._settings.openai_api_key,
                temperature=0.2,
            )
            response = await llm.ainvoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt),
                ]
            )
            content = response.content
            if isinstance(content, list):
                content = "".join(
                    block.get("text", "") if isinstance(block, dict) else str(block)
                    for block in content
                )
            return _parse_json(str(content), fallback)
        except Exception as exc:
            logger.warning("LLM invocation failed: %s — using fallback", exc)
            return fallback


def _parse_json(text: str, fallback: dict[str, Any]) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                parsed = json.loads(text[start : end + 1])
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass
    return fallback
