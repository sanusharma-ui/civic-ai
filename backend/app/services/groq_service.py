from collections.abc import AsyncIterator
from typing import Any

from groq import APIConnectionError, APIStatusError, AsyncGroq

from app.core.config import settings


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
            self._client = AsyncGroq(api_key=settings.groq_api_key)

        return self._client

    async def generate(
        self,
        *,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        try:
            response = await self.client.chat.completions.create(
                model=settings.groq_model,
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
        }

    async def stream(
        self,
        *,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        try:
            stream = await self.client.chat.completions.create(
                model=settings.groq_model,
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
