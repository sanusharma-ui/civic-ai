import sys

code = """
# ---------------------------------------------------------------------------
# Conversations CRUD
# ---------------------------------------------------------------------------

async def insert_conversation(*, id: str, agent_id: str, title: str | None = None) -> None:
    async with aiosqlite.connect(_DB_PATH) as conn:
        await conn.execute(
            "INSERT INTO conversations (id, agent_id, title) VALUES (?, ?, ?)",
            (id, agent_id, title)
        )
        await conn.commit()

async def get_conversation_row(id: str) -> dict[str, Any] | None:
    async with aiosqlite.connect(_DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT * FROM conversations WHERE id = ?", (id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def list_conversation_rows() -> list[dict[str, Any]]:
    async with aiosqlite.connect(_DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT * FROM conversations ORDER BY updated_at DESC") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def delete_conversation_row(id: str) -> None:
    async with aiosqlite.connect(_DB_PATH) as conn:
        await conn.execute("DELETE FROM conversations WHERE id = ?", (id,))
        await conn.commit()

async def insert_message(*, id: str, conversation_id: str, role: str, content: str) -> None:
    async with aiosqlite.connect(_DB_PATH) as conn:
        await conn.execute(
            "INSERT INTO messages (id, conversation_id, role, content) VALUES (?, ?, ?, ?)",
            (id, conversation_id, role, content)
        )
        await conn.execute(
            "UPDATE conversations SET updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = ?",
            (conversation_id,)
        )
        await conn.commit()

async def get_messages_for_conversation(conversation_id: str) -> list[dict[str, Any]]:
    async with aiosqlite.connect(_DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC", (conversation_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
"""

with open('d:/Projects/civic-ai/backend/app/core/database.py', 'a') as f:
    f.write(code)
