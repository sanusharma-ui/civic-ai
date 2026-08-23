"""Chat API routes — non-streaming and SSE streaming."""

from __future__ import annotations

import json
import base64
from collections.abc import AsyncIterator
from io import BytesIO

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pypdf import PdfReader

from app.agents.registry import get_agent
from app.schemas.chat import AgentMeta, ChatRequest, ChatResponse, StructuredBlock
from app.services.agent_service import agent_service
from app.services.chat_service import chat_service
from app.services.groq_service import GroqServiceError

router = APIRouter()

MAX_UPLOAD_BYTES = 8 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


@router.post("/upload")
async def upload_media(file: UploadFile = File(...)) -> dict:
    """Extract PDF text locally or return an image data URL for vision chat."""
    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_IMAGE_TYPES and content_type != "application/pdf":
        raise HTTPException(status_code=415, detail="Only JPG, PNG, WEBP, GIF, and PDF files are supported.")
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File must be 8 MB or smaller.")
    name = file.filename or "attachment"
    if content_type == "application/pdf":
        try:
            reader = PdfReader(BytesIO(data))
            extracted = "\n\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception as exc:
            raise HTTPException(status_code=400, detail="This PDF could not be read.") from exc
        if not extracted.strip():
            raise HTTPException(status_code=400, detail="This PDF has no selectable text. Upload a text PDF or image instead.")
        return {
            "kind": "pdf",
            "name": name,
            "mime_type": content_type,
            "data_url": f"data:{content_type};base64,{base64.b64encode(data).decode('ascii')}",
            "extracted_text": extracted[:50000],
        }
    encoded = base64.b64encode(data).decode("ascii")
    return {"kind": "image", "name": name, "mime_type": content_type, "data_url": f"data:{content_type};base64,{encoded}"}


# ---------------------------------------------------------------------------
# History helper
# ---------------------------------------------------------------------------


async def _history_for_llm(
    conversation_id: str | None,
    request: ChatRequest,
) -> list[dict[str, str]]:
    if request.history:
        return [msg.model_dump() for msg in request.history]
    if not conversation_id:
        return []
    try:
        conversation = await chat_service.get_conversation(conversation_id)
        return [
            {"role": m.role, "content": m.content}
            for m in conversation.messages[-12:]
        ]
    except ValueError:
        return []


# ---------------------------------------------------------------------------
# POST /chat — Non-streaming
# ---------------------------------------------------------------------------


@router.post("", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    """
    Full agentic response (non-streaming).

    Runs the complete ReAct loop and returns structured canvas blocks
    alongside the raw response text.
    """
    try:
        agent_cfg = get_agent(payload.agent_id)
        conversation = await chat_service.get_or_create(
            agent_id=payload.agent_id,
            conversation_id=payload.conversation_id,
        )
        history = await _history_for_llm(conversation.id, payload)

        result = await agent_service.respond(
            agent_id=payload.agent_id,
            user_message=payload.message,
            conversation_history=history,
        )

        await chat_service.add_message(conversation.id, "user", payload.message)
        await chat_service.add_message(conversation.id, "assistant", result["response"])

        agent_meta = AgentMeta(
            id=result["agent"]["id"],
            name=result["agent"]["name"],
            version=result["agent"]["version"],
        )

        return ChatResponse(
            conversation_id=conversation.id,
            agent=agent_meta,
            response=result["response"],
            structured=result["structured"],
            model=result["model"],
            usage=result["usage"],
            retrieved_context=result["retrieved_context"],
        )

    except GroqServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# POST /chat/stream — SSE streaming
# ---------------------------------------------------------------------------


@router.post("/stream")
async def stream_chat(payload: ChatRequest) -> StreamingResponse:
    """
    Streaming agentic response via Server-Sent Events.

    Event types:
    - ``thinking`` : agent loop is running (show spinner)
    - ``block``    : one structured canvas block
    - ``done``     : final metadata summary
    - ``error``    : error detail
    """

    async def event_stream() -> AsyncIterator[str]:
        conversation = None
        try:
            get_agent(payload.agent_id)  # validate early
            conversation = await chat_service.get_or_create(
                agent_id=payload.agent_id,
                conversation_id=payload.conversation_id,
            )
            history = await _history_for_llm(conversation.id, payload)

            # Emit start event
            yield _sse(
                {
                    "type": "start",
                    "conversation_id": conversation.id,
                    "agent_id": payload.agent_id,
                }
            )

            full_response = ""

            async for event in agent_service.stream_response(
                agent_id=payload.agent_id,
                user_message=payload.message,
                conversation_history=history,
                attachments=payload.attachments,
            ):
                event_type = event.get("type")

                if event_type == "thinking":
                    yield _sse(event)

                elif event_type == "block":
                    yield _sse(event)

                elif event_type == "done":
                    full_response = event.get("response", "")
                    # Persist to conversation history
                    await chat_service.add_message(conversation.id, "user", payload.message)
                    await chat_service.add_message(conversation.id, "assistant", full_response)
                    yield _sse(
                        {
                            **event,
                            "conversation_id": conversation.id,
                        }
                    )

                elif event_type == "error":
                    yield _sse(
                        {
                            **event,
                            "conversation_id": conversation.id if conversation else None,
                        }
                    )

        except (GroqServiceError, ValueError) as exc:
            yield _sse(
                {
                    "type": "error",
                    "conversation_id": conversation.id if conversation else None,
                    "detail": str(exc),
                }
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream; charset=utf-8",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# SSE helper
# ---------------------------------------------------------------------------


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"
