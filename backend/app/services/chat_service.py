from app.models.conversation import Conversation


class ChatService:
    """
    Minimal in-memory conversation storage.

    This is intentionally small so it can be replaced by PostgreSQL/Supabase
    later without changing the routes or agent orchestration layer.
    """

    def __init__(self) -> None:
        self._conversations: dict[str, Conversation] = {}

    def create_conversation(
        self,
        *,
        agent_id: str,
        title: str | None = None,
    ) -> Conversation:
        conversation = Conversation(agent_id=agent_id, title=title)
        self._conversations[conversation.id] = conversation
        return conversation

    def get_or_create(
        self,
        *,
        agent_id: str,
        conversation_id: str | None,
    ) -> Conversation:
        if conversation_id:
            conversation = self.get_conversation(conversation_id)
            if conversation.agent_id != agent_id:
                raise ValueError(
                    "Conversation belongs to a different agent."
                )
            return conversation

        return self.create_conversation(agent_id=agent_id)

    def get_conversation(self, conversation_id: str) -> Conversation:
        conversation = self._conversations.get(conversation_id)

        if conversation is None:
            raise ValueError(f"Conversation '{conversation_id}' was not found.")

        return conversation

    def list_conversations(self) -> list[Conversation]:
        return sorted(
            self._conversations.values(),
            key=lambda conversation: conversation.updated_at,
            reverse=True,
        )

    def delete_conversation(self, conversation_id: str) -> None:
        if conversation_id not in self._conversations:
            raise ValueError(f"Conversation '{conversation_id}' was not found.")

        del self._conversations[conversation_id]


chat_service = ChatService()
