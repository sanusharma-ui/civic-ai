from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class MessageRead(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


class ConversationCreate(BaseModel):
    agent_id: str = Field(default="rti", examples=["rti", "consumer"])
    title: str | None = Field(default=None, max_length=120)


class ConversationRead(BaseModel):
    id: str
    agent_id: str
    title: str | None = None
    created_at: datetime
    updated_at: datetime
    messages: list[MessageRead] = Field(default_factory=list)


class ConversationList(BaseModel):
    conversations: list[ConversationRead]
