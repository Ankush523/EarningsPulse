"""LLM client with structured JSON output and deterministic fallback."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

# Ordered fallbacks when the configured Google model is unavailable on an API key.
GOOGLE_MODEL_FALLBACKS: tuple[str, ...] = (
    "gemma-4-31b-it",
    "gemma-4-26b-a4b-it",
    "gemini-2.5-flash",
    "gemini-3.5-flash",
)


class LLMClient:
    """OpenAI-first LLM wrapper with Google/Gemma fallback and heuristic default."""

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

    @property
    def enabled(self) -> bool:
        return bool(self._settings.openai_api_key or self._settings.google_api_key)

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

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        if self._settings.openai_api_key:
            try:
                return await self._invoke_openai(messages, fallback)
            except Exception as exc:
                logger.warning("OpenAI invocation failed: %s", exc)
                if self._settings.google_api_key:
                    logger.info("Trying Google LLM fallback")
                    try:
                        return await self._invoke_google(messages, fallback)
                    except Exception as google_exc:
                        logger.warning(
                            "Google LLM invocation failed: %s — using fallback",
                            google_exc,
                        )
                else:
                    logger.warning("No Google fallback configured — using deterministic fallback")
                return fallback

        try:
            return await self._invoke_google(messages, fallback)
        except Exception as exc:
            logger.warning("Google LLM invocation failed: %s — using fallback", exc)
            return fallback

    async def _invoke_openai(
        self,
        messages: list[SystemMessage | HumanMessage],
        fallback: dict[str, Any],
    ) -> dict[str, Any]:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=self._settings.llm_model,
            api_key=self._settings.openai_api_key,
            temperature=0.2,
        )
        response = await llm.ainvoke(messages)
        return _parse_json(_content_to_text(response.content), fallback)

    async def _invoke_google(
        self,
        messages: list[SystemMessage | HumanMessage],
        fallback: dict[str, Any],
    ) -> dict[str, Any]:
        import google.generativeai as genai

        genai.configure(api_key=self._settings.google_api_key)
        system_prompt = next(
            (message.content for message in messages if isinstance(message, SystemMessage)),
            "",
        )
        user_prompt = next(
            (message.content for message in messages if isinstance(message, HumanMessage)),
            "",
        )
        prompt = f"{system_prompt}\n\n{user_prompt}".strip()

        last_error: Exception | None = None
        for model_name in self._google_model_candidates():
            try:
                model = genai.GenerativeModel(
                    model_name=model_name,
                    generation_config={"temperature": 0.2},
                )
                response = await asyncio.to_thread(model.generate_content, prompt)
                logger.info("Google LLM forecast succeeded (%s)", model_name)
                return _parse_json(response.text, fallback)
            except Exception as exc:
                last_error = exc
                if _is_google_model_unavailable(exc):
                    logger.warning("Google model %s unavailable: %s", model_name, exc)
                    continue
                raise

        if last_error is not None:
            raise last_error
        raise RuntimeError("No Google models configured")

    def _google_model_candidates(self) -> list[str]:
        configured = self._settings.google_llm_model.strip()
        candidates = [configured, *GOOGLE_MODEL_FALLBACKS]
        seen: set[str] = set()
        ordered: list[str] = []
        for name in candidates:
            if name and name not in seen:
                seen.add(name)
                ordered.append(name)
        return ordered


def _is_google_model_unavailable(exc: Exception) -> bool:
    message = str(exc).lower()
    return "not found" in message or "not supported for generatecontent" in message


def _content_to_text(content: Any) -> str:
    if isinstance(content, list):
        return "".join(
            block.get("text", "") if isinstance(block, dict) else str(block) for block in content
        )
    return str(content)


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
