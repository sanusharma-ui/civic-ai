import json
import logging
from pathlib import Path
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

_DB_PATH = Path(__file__).resolve().parents[2] / "civic_ai.db"

# ---------------------------------------------------------------------------
# Schema DDL
# ---------------------------------------------------------------------------

_SQLITE_DDL = """
CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id          TEXT PRIMARY KEY,
    domain      TEXT NOT NULL,
    title       TEXT NOT NULL,
    content     TEXT NOT NULL,
    source      TEXT NOT NULL,
    metadata    TEXT NOT NULL DEFAULT '{}',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_kc_domain ON knowledge_chunks (domain);

CREATE TABLE IF NOT EXISTS conversations (
    id          TEXT PRIMARY KEY,
    agent_id    TEXT NOT NULL,
    title       TEXT,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS messages (
    id              TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content         TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_msg_conv ON messages (conversation_id, created_at);
"""

_PG_DDL = """
CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id          TEXT PRIMARY KEY,
    domain      TEXT NOT NULL,
    title       TEXT NOT NULL,
    content     TEXT NOT NULL,
    source      TEXT NOT NULL,
    metadata    TEXT NOT NULL DEFAULT '{}',
    created_at  TEXT NOT NULL DEFAULT to_char(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')
);

CREATE INDEX IF NOT EXISTS idx_kc_domain ON knowledge_chunks (domain);

CREATE TABLE IF NOT EXISTS conversations (
    id          TEXT PRIMARY KEY,
    agent_id    TEXT NOT NULL,
    title       TEXT,
    created_at  TEXT NOT NULL DEFAULT to_char(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'),
    updated_at  TEXT NOT NULL DEFAULT to_char(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')
);

CREATE TABLE IF NOT EXISTS messages (
    id              TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content         TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT to_char(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')
);

CREATE INDEX IF NOT EXISTS idx_msg_conv ON messages (conversation_id, created_at);
"""

import aiosqlite
try:
    import asyncpg
except ImportError:
    asyncpg = None

class DatabaseManager:
    def __init__(self):
        self.is_postgres = bool(settings.database_url and settings.database_url.startswith("postgres"))
        self.pool = None
        if self.is_postgres and not asyncpg:
            logger.error("PostgreSQL URL provided but asyncpg is not installed!")

    def _to_pg_query(self, query: str) -> str:
        parts = query.split("?")
        res = parts[0]
        for i, part in enumerate(parts[1:], 1):
            res += f"${i}" + part
        return res

    async def init_db(self):
        if self.is_postgres:
            if not self.pool:
                self.pool = await asyncpg.create_pool(settings.database_url)
            async with self.pool.acquire() as conn:
                await conn.execute(_PG_DDL)
            logger.info("Connected to PostgreSQL database.")
        else:
            async with aiosqlite.connect(_DB_PATH) as conn:
                await conn.executescript(_SQLITE_DDL)
            logger.info("Database initialised at %s", _DB_PATH)

    async def execute(self, query: str, *args):
        if self.is_postgres:
            if not self.pool:
                self.pool = await asyncpg.create_pool(settings.database_url)
            pg_query = self._to_pg_query(query)
            async with self.pool.acquire() as conn:
                await conn.execute(pg_query, *args)
        else:
            async with aiosqlite.connect(_DB_PATH) as conn:
                await conn.execute(query, args)
                await conn.commit()

    async def fetch_all(self, query: str, *args) -> list[dict]:
        if self.is_postgres:
            if not self.pool:
                self.pool = await asyncpg.create_pool(settings.database_url)
            pg_query = self._to_pg_query(query)
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(pg_query, *args)
                return [dict(r) for r in rows]
        else:
            async with aiosqlite.connect(_DB_PATH) as conn:
                conn.row_factory = aiosqlite.Row
                async with conn.execute(query, args) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(r) for r in rows]

    async def fetch_one(self, query: str, *args) -> dict | None:
        if self.is_postgres:
            if not self.pool:
                self.pool = await asyncpg.create_pool(settings.database_url)
            pg_query = self._to_pg_query(query)
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(pg_query, *args)
                return dict(row) if row else None
        else:
            async with aiosqlite.connect(_DB_PATH) as conn:
                conn.row_factory = aiosqlite.Row
                async with conn.execute(query, args) as cursor:
                    row = await cursor.fetchone()
                    return dict(row) if row else None

db_manager = DatabaseManager()

async def init_db() -> None:
    await db_manager.init_db()

async def upsert_chunk(
    *,
    id: str,
    domain: str,
    title: str,
    content: str,
    source: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    query = """
    INSERT INTO knowledge_chunks (id, domain, title, content, source, metadata)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
        title    = excluded.title,
        content  = excluded.content,
        source   = excluded.source,
        metadata = excluded.metadata
    """
    await db_manager.execute(query, id, domain, title, content, source, json.dumps(metadata or {}))

async def search_chunks(
    *,
    domain: str,
    query: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    terms = [t.lower() for t in query.replace("?", " ").replace(",", " ").split() if len(t) > 2]
    if not terms:
        return []
    
    conditions = " AND ".join(["(LOWER(title) LIKE ? OR LOWER(content) LIKE ?)"] * len(terms))
    params: list[Any] = []
    for term in terms:
        params.append(f"%{term}%")
        params.append(f"%{term}%")
    params.append(domain)
    params.append(limit)
    
    sql = f"""
        SELECT id, domain, title, content, source, metadata
        FROM   knowledge_chunks
        WHERE  ({conditions})
          AND  domain = ?
        LIMIT  ?
    """
    try:
        rows = await db_manager.fetch_all(sql, *params)
        for row in rows:
            row['metadata'] = json.loads(row['metadata'])
        return rows
    except Exception as exc:
        logger.warning("DB search failed (table may be empty): %s", exc)
        return []

async def count_chunks(domain: str | None = None) -> int:
    sql = "SELECT COUNT(*) FROM knowledge_chunks"
    params = []
    if domain:
        sql += " WHERE domain = ?"
        params.append(domain)
    try:
        row = await db_manager.fetch_one(sql, *params)
        return int(row["count"] if "count" in row else list(row.values())[0]) if row else 0
    except Exception:
        return 0

async def insert_conversation(*, id: str, agent_id: str, title: str | None = None) -> None:
    await db_manager.execute(
        "INSERT INTO conversations (id, agent_id, title) VALUES (?, ?, ?)",
        id, agent_id, title
    )

async def get_conversation_row(id: str) -> dict[str, Any] | None:
    return await db_manager.fetch_one("SELECT * FROM conversations WHERE id = ?", id)

async def list_conversation_rows() -> list[dict[str, Any]]:
    return await db_manager.fetch_all("SELECT * FROM conversations ORDER BY updated_at DESC")

async def delete_conversation_row(id: str) -> None:
    await db_manager.execute("DELETE FROM conversations WHERE id = ?", id)

async def insert_message(*, id: str, conversation_id: str, role: str, content: str) -> None:
    await db_manager.execute(
        "INSERT INTO messages (id, conversation_id, role, content) VALUES (?, ?, ?, ?)",
        id, conversation_id, role, content
    )
    if db_manager.is_postgres:
        await db_manager.execute(
            "UPDATE conversations SET updated_at = to_char(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"') WHERE id = ?",
            conversation_id
        )
    else:
        await db_manager.execute(
            "UPDATE conversations SET updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = ?",
            conversation_id
        )

async def get_messages_for_conversation(conversation_id: str) -> list[dict[str, Any]]:
    return await db_manager.fetch_all("SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC", conversation_id)
