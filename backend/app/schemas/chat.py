"""Pydantic schemas for the chat API."""

from typing import Any, Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Structured response blocks
# ---------------------------------------------------------------------------


class StructuredBlock(BaseModel):
    """
    A single visual block in the agent's canvas response.

    The frontend renders each block type differently:
    - ``header``        → Bold title card at the top
    - ``section``       → Collapsible information section
    - ``steps``         → Numbered action-step list
    - ``draft``         → Copyable document panel (RTI / complaint letter)
    - ``disclaimer``    → Warning / advisory note
    - ``clarification`` → Agent asking the user a question
    - ``info``          → Neutral information callout
    - ``warning``       → Highlighted warning callout
    """

    type: Literal[
        "header",
        "section",
        "steps",
        "draft",
        "disclaimer",
        "clarification",
        "info",
        "warning",
    ]
    title: str = ""
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Chat request / response
# ---------------------------------------------------------------------------


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=12000)


class ChatAttachment(BaseModel):
    kind: Literal["image", "pdf"]
    name: str = Field(max_length=255)
    mime_type: str = Field(max_length=100)
    data_url: str | None = None
    extracted_text: str | None = Field(default=None, max_length=50000)


class ChatRequest(BaseModel):
    agent_id: str = Field(default="rti", examples=["rti", "consumer"])
    message: str = Field(min_length=1, max_length=12000)
    conversation_id: str | None = None
    history: list[ChatMessage] = Field(default_factory=list)
    attachments: list[ChatAttachment] = Field(default_factory=list, max_length=4)


class AgentMeta(BaseModel):
    id: str
    name: str
    version: str


class ChatResponse(BaseModel):
    conversation_id: str
    agent: AgentMeta
    response: str                       # raw markdown fallback
    structured: list[StructuredBlock]   # canvas blocks (primary)
    model: str
    usage: dict | None = None
    retrieved_context: list[dict] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# SSE stream events
# ---------------------------------------------------------------------------


class StreamEvent(BaseModel):
    """
    Server-sent event envelope.

    Types:
    - ``start``       → Metadata before streaming begins
    - ``token``       → Incremental text token
    - ``block``       → Complete structured block (emitted after streaming)
    - ``done``        → Final summary + full response
    - ``error``       → Error detail
    """

    type: Literal["start", "token", "block", "done", "error"]
    conversation_id: str | None = None
    token: str | None = None
    block: StructuredBlock | None = None
    response: str | None = None
    structured: list[StructuredBlock] | None = None
    detail: str | None = None
    agent: AgentMeta | None = None
    model: str | None = None
    retrieved_context: list[dict] | None = None
