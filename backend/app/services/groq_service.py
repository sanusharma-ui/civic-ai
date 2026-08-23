"""
Groq LLM service.

Wraps the Groq async client with:
- Standard generate() for single completions
- generate_with_tools() for the agentic tool-calling loop
- stream() for token-by-token streaming
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from groq import APIConnectionError, APIStatusError, AsyncGroq

from app.core.config import settings

logger = logging.getLogger(__name__)


class GroqServiceError(RuntimeError):
    pass


class GroqService:

    def __init__(self) -> None:
        self._client: AsyncGroq | None = None

    @property
    def client(self) -> AsyncGroq:
        if not settings.groq_api_key:
            raise GroqServiceError(
                "GROQ_API_KEY is not configured. Add it to backend/.env."
            )
        if self._client is None:
            self._client = AsyncGroq(
                api_key=settings.groq_api_key,
                timeout=settings.groq_timeout_seconds,
                max_retries=0,
            )
        return self._client

    # ------------------------------------------------------------------
    # Standard (non-streaming, no tools)
    # ------------------------------------------------------------------

    async def generate(
        self,
        *,
        messages: list[dict[str, Any]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        """Single-turn completion. Returns content, model, usage."""
        try:
            response = await self.client.chat.completions.create(
                model=model or settings.groq_model,
                messages=messages,
                temperature=temperature or settings.groq_temperature,
                max_tokens=max_tokens or settings.groq_max_tokens,
            )
        except (APIConnectionError, APIStatusError) as exc:
            raise GroqServiceError(f"Groq request failed: {exc}") from exc

        message = response.choices[0].message
        return {
            "content": message.content or "",
            "model": response.model,
            "usage": response.usage.model_dump() if response.usage else None,
            "tool_calls": None,
        }

    # ------------------------------------------------------------------
    # Tool-calling (agentic loop step)
    # ------------------------------------------------------------------

    async def generate_with_tools(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        """
        Single completion step with tool schemas.

        Returns a dict with:
        - ``content``    : str | None  — text content (if final answer)
        - ``tool_calls`` : list | None — tool calls requested by LLM
        - ``model``      : str
        - ``usage``      : dict | None
        """
        try:
            response = await self.client.chat.completions.create(
                model=model or settings.groq_model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=temperature or settings.groq_temperature,
                max_tokens=max_tokens or settings.groq_max_tokens,
            )
        except (APIConnectionError, APIStatusError) as exc:
            # If the model doesn't support tool calling, fall back to plain generate
            logger.warning(
                "Tool-calling failed (model may not support it): %s. "
                "Falling back to plain generate.",
                exc,
            )
            return await self.generate(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        choice = response.choices[0]
        message = choice.message

        # Normalise tool_calls into serialisable dicts
        tool_calls = None
        if message.tool_calls:
            tool_calls = []
            for tc in message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except (json.JSONDecodeError, TypeError):
                    args = {}
                tool_calls.append(
                    {
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": args,
                    }
                )

        return {
            "content": message.content or "",
            "tool_calls": tool_calls,
            "model": response.model,
            "usage": response.usage.model_dump() if response.usage else None,
        }

    # ------------------------------------------------------------------
    # Streaming
    # ------------------------------------------------------------------

    async def stream(
        self,
        *,
        messages: list[dict[str, Any]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        model: str | None = None,
    ) -> AsyncIterator[str]:
        """Token-by-token streaming (no tools — used after agentic loop)."""
        try:
            stream = await self.client.chat.completions.create(
                model=model or settings.groq_model,
                messages=messages,
                temperature=temperature or settings.groq_temperature,
                max_tokens=max_tokens or settings.groq_max_tokens,
                stream=True,
            )
            async for chunk in stream:
                if not chunk.choices:
                    continue
                token = chunk.choices[0].delta.content
                if token:
                    yield token
        except (APIConnectionError, APIStatusError) as exc:
            raise GroqServiceError(f"Groq stream failed: {exc}") from exc


groq_service = GroqService()
