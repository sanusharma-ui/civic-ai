import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.agents.registry import get_agent
from app.core.config import settings
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.agent_service import agent_service
from app.services.chat_service import chat_service
from app.services.groq_service import GroqServiceError
from app.services.retrieval_service import retrieval_service


router = APIRouter()


def _history_for_llm(conversation_id: str | None, request: ChatRequest):
    if request.history:
        return [message.model_dump() for message in request.history]

    if not conversation_id:
        return []

    conversation = chat_service.get_conversation(conversation_id)
    return [
        {"role": message.role, "content": message.content}
        for message in conversation.messages[-12:]
    ]


@router.post("", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    try:
        agent = get_agent(payload.agent_id)
        conversation = chat_service.get_or_create(
            agent_id=payload.agent_id,
            conversation_id=payload.conversation_id,
        )
        history = _history_for_llm(conversation.id, payload)
        documents = await retrieval_service.retrieve(
            agent=agent,
            query=payload.message,
        )
        verified_context = retrieval_service.format_context(documents)

        result = await agent_service.respond(
            agent_id=payload.agent_id,
            user_message=payload.message,
            conversation_history=history,
            verified_context=verified_context,
        )

        conversation.add_message("user", payload.message)
        conversation.add_message("assistant", result["response"])

        return ChatResponse(
            conversation_id=conversation.id,
            agent=result["agent"],
            response=result["response"],
            model=result["model"],
            usage=result["usage"],
            retrieved_context=retrieval_service.serialize(documents),
        )
    except GroqServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/stream")
async def stream_chat(payload: ChatRequest) -> StreamingResponse:
    async def event_stream() -> AsyncIterator[str]:
        response_parts: list[str] = []
        conversation = None

        try:
            agent = get_agent(payload.agent_id)
            conversation = chat_service.get_or_create(
                agent_id=payload.agent_id,
                conversation_id=payload.conversation_id,
            )
            history = _history_for_llm(conversation.id, payload)
            documents = await retrieval_service.retrieve(
                agent=agent,
                query=payload.message,
            )
            verified_context = retrieval_service.format_context(documents)

            yield _sse(
                {
                    "type": "start",
                    "conversation_id": conversation.id,
                    "agent": {
                        "id": agent.agent_id,
                        "name": agent.name,
                        "version": agent.version,
                    },
                    "model": settings.groq_model,
                    "retrieved_context": retrieval_service.serialize(
                        documents
                    ),
                }
            )

            async for token in agent_service.stream_response(
                agent_id=payload.agent_id,
                user_message=payload.message,
                conversation_history=history,
                verified_context=verified_context,
            ):
                response_parts.append(token)
                yield _sse({"type": "token", "token": token})

            full_response = "".join(response_parts)
            conversation.add_message("user", payload.message)
            conversation.add_message("assistant", full_response)

            yield _sse(
                {
                    "type": "done",
                    "conversation_id": conversation.id,
                    "response": full_response,
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
            "X-Accel-Buffering": "no",
        },
    )


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
