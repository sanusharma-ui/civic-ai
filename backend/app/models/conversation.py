from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from app.models.message import Message


@dataclass
class Conversation:
    agent_id: str
    title: str | None = None
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    messages: list[Message] = field(default_factory=list)

    def add_message(self, role: str, content: str) -> Message:
        message = Message(role=role, content=content)  # type: ignore[arg-type]
        self.messages.append(message)
        self.updated_at = datetime.now(timezone.utc)
        return message
