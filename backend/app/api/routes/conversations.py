from fastapi import APIRouter, HTTPException, Response

from app.agents.registry import get_agent
from app.models.conversation import Conversation
from app.schemas.conversation import (
    ConversationCreate,
    ConversationList,
    ConversationRead,
    MessageRead,
)
from app.services.chat_service import chat_service


router = APIRouter()


def _to_conversation_read(
    conversation: Conversation,
) -> ConversationRead:
    return ConversationRead(
        id=conversation.id,
        agent_id=conversation.agent_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[
            MessageRead(
                id=message.id,
                role=message.role,
                content=message.content,
                created_at=message.created_at,
            )
            for message in conversation.messages
        ],
    )


@router.post("", response_model=ConversationRead, status_code=201)
async def create_conversation(
    payload: ConversationCreate,
) -> ConversationRead:
    try:
        get_agent(payload.agent_id)
        conversation = await chat_service.create_conversation(
            agent_id=payload.agent_id,
            title=payload.title,
        )
        return _to_conversation_read(conversation)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=ConversationList)
async def list_conversations() -> ConversationList:
    return ConversationList(
        conversations=[
            _to_conversation_read(conversation)
            for conversation in await chat_service.list_conversations()
        ]
    )


@router.get("/{conversation_id}", response_model=ConversationRead)
async def get_conversation(
    conversation_id: str,
) -> ConversationRead:
    try:
        return _to_conversation_read(
            await chat_service.get_conversation(conversation_id)
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(conversation_id: str) -> Response:
    try:
        await chat_service.delete_conversation(conversation_id)
        return Response(status_code=204)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
