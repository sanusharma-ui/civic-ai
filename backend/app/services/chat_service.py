from datetime import timezone
from dateutil.parser import parse

from app.models.conversation import Conversation
from app.models.message import Message
from app.core import database


class ChatService:
    """
    Database-backed conversation storage.
    """

    async def create_conversation(
        self,
        *,
        agent_id: str,
        title: str | None = None,
    ) -> Conversation:
        conversation = Conversation(agent_id=agent_id, title=title)
        await database.insert_conversation(
            id=conversation.id, agent_id=conversation.agent_id, title=conversation.title
        )
        return conversation

    async def get_or_create(
        self,
        *,
        agent_id: str,
        conversation_id: str | None,
    ) -> Conversation:
        if conversation_id:
            conversation = await self.get_conversation(conversation_id)
            if conversation.agent_id != agent_id:
                raise ValueError(
                    "Conversation belongs to a different agent."
                )
            return conversation

        return await self.create_conversation(agent_id=agent_id)

    async def get_conversation(self, conversation_id: str) -> Conversation:
        row = await database.get_conversation_row(conversation_id)
        if not row:
            raise ValueError(f"Conversation '{conversation_id}' was not found.")

        conv = Conversation(agent_id=row['agent_id'], title=row['title'], id=row['id'])
        if row.get('created_at'):
            conv.created_at = parse(row['created_at']).replace(tzinfo=timezone.utc)
            conv.updated_at = parse(row['updated_at']).replace(tzinfo=timezone.utc)

        msg_rows = await database.get_messages_for_conversation(conversation_id)
        for m in msg_rows:
            msg = Message(id=m['id'], role=m['role'], content=m['content'])
            if m.get('created_at'):
                msg.created_at = parse(m['created_at']).replace(tzinfo=timezone.utc)
            conv.messages.append(msg)

        return conv

    async def list_conversations(self) -> list[Conversation]:
        rows = await database.list_conversation_rows()
        res = []
        for row in rows:
            conv = Conversation(agent_id=row['agent_id'], title=row['title'], id=row['id'])
            if row.get('created_at'):
                conv.created_at = parse(row['created_at']).replace(tzinfo=timezone.utc)
                conv.updated_at = parse(row['updated_at']).replace(tzinfo=timezone.utc)
            res.append(conv)
        return res

    async def delete_conversation(self, conversation_id: str) -> None:
        row = await database.get_conversation_row(conversation_id)
        if not row:
            raise ValueError(f"Conversation '{conversation_id}' was not found.")

        await database.delete_conversation_row(conversation_id)

    async def add_message(self, conversation_id: str, role: str, content: str) -> Message:
        # First append locally if needed, but here we just insert into db.
        msg = Message(role=role, content=content)
        await database.insert_message(
            id=msg.id,
            conversation_id=conversation_id,
            role=role,
            content=content
        )
        return msg


chat_service = ChatService()
