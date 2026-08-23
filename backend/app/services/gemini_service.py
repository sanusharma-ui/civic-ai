"""Gemini streaming client for image and PDF understanding."""

from __future__ import annotations

import base64
import json
from collections.abc import AsyncIterator

import httpx

from app.core.config import settings
from app.schemas.chat import ChatAttachment


class GeminiServiceError(RuntimeError):
    pass


class GeminiService:
    def __init__(self) -> None:
        self._client = None

    @property
    def client(self):
        if not settings.gemini_api_key:
            raise GeminiServiceError(
                "GEMINI_API_KEY is not configured. Add it to backend/.env."
            )
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(settings.gemini_timeout_seconds)
            )
        return self._client

    async def stream(
        self,
        *,
        prompt: str,
        attachments: list[ChatAttachment],
        system_instruction: str,
    ) -> AsyncIterator[str]:
        """Stream one direct Gemini multimodal request; no extra model hop."""
        try:
            parts: list[dict] = []
            for attachment in attachments:
                if not attachment.data_url or "," not in attachment.data_url:
                    continue
                encoded = attachment.data_url.split(",", 1)[1]
                parts.append({
                    "inline_data": {
                        "mime_type": attachment.mime_type,
                        "data": encoded,
                    }
                })
            parts.insert(0, {"text": f"{system_instruction}\n\nUSER REQUEST:\n{prompt}"})

            url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{settings.gemini_model}:streamGenerateContent?alt=sse"
            )
            async with self.client.stream(
                "POST",
                url,
                headers={"x-goog-api-key": settings.gemini_api_key},
                json={
                    "contents": [{"role": "user", "parts": parts}],
                    "generationConfig": {
                        "temperature": settings.groq_temperature,
                        "maxOutputTokens": settings.groq_max_tokens,
                    },
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    payload = json.loads(line[5:].strip())
                    for candidate in payload.get("candidates", []):
                        for part in candidate.get("content", {}).get("parts", []):
                            text = part.get("text")
                            if text:
                                yield text
        except GeminiServiceError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise GeminiServiceError(f"Gemini request failed: {exc}") from exc


gemini_service = GeminiService()
