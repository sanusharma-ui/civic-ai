from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=12000)


class ChatRequest(BaseModel):
    agent_id: str = Field(default="rti", examples=["rti", "consumer"])
    message: str = Field(min_length=1, max_length=12000)
    conversation_id: str | None = None
    history: list[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    conversation_id: str
    agent: dict[str, str]
    response: str
    model: str
    usage: dict | None = None
    retrieved_context: list[dict] = Field(default_factory=list)


class StreamEvent(BaseModel):
    type: Literal["start", "token", "done", "error"]
    conversation_id: str | None = None
    token: str | None = None
    response: str | None = None
    detail: str | None = None
    agent: dict[str, str] | None = None
    model: str | None = None
    retrieved_context: list[dict] | None = None
