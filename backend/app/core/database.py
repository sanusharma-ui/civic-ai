"""
Async SQLite database layer.

Provides a lightweight, zero-setup local store for knowledge chunks and
persistent conversations. The interface is kept intentionally thin so that
swapping to Supabase / PostgreSQL later requires only changing this module.
"""

import json
import logging
from pathlib import Path
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)

_DB_PATH = Path(__file__).resolve().parents[2] / "civic_ai.db"


# ---------------------------------------------------------------------------
# Schema DDL
# ---------------------------------------------------------------------------

_DDL = """
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


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


async def init_db() -> None:
    """Create all tables (idempotent). Call once at app startup."""
    async with aiosqlite.connect(_DB_PATH) as conn:
        await conn.executescript(_DDL)
        await conn.commit()
    logger.info("Database initialised at %s", _DB_PATH)


# ---------------------------------------------------------------------------
# Knowledge Chunks CRUD
# ---------------------------------------------------------------------------


async def upsert_chunk(
    *,
    id: str,
    domain: str,
    title: str,
    content: str,
    source: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Insert or replace a knowledge chunk."""
    async with aiosqlite.connect(_DB_PATH) as conn:
        await conn.execute(
            """
            INSERT INTO knowledge_chunks (id, domain, title, content, source, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title    = excluded.title,
                content  = excluded.content,
                source   = excluded.source,
                metadata = excluded.metadata
            """,
            (
                id,
                domain,
                title,
                content,
                source,
                json.dumps(metadata or {}),
            ),
        )
        await conn.commit()


async def search_chunks(
    *,
    domain: str,
    query: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """
    Keyword search over knowledge_chunks for a given domain.

    Uses LIKE matching across title + content.
    Returns empty list gracefully when the table is empty.
    """
    terms = [
        t.lower()
        for t in query.replace("?", " ").replace(",", " ").split()
        if len(t) > 2
    ]

    if not terms:
        return []

    # Build WHERE clause: each term must appear in title OR content
    conditions = " AND ".join(
        ["(LOWER(title) LIKE ? OR LOWER(content) LIKE ?)"] * len(terms)
    )
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
    """  # noqa: S608 — internal query, no user SQL

    try:
        async with aiosqlite.connect(_DB_PATH) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(sql, params) as cursor:
                rows = await cursor.fetchall()
                return [
                    {
                        "id": row["id"],
                        "domain": row["domain"],
                        "title": row["title"],
                        "content": row["content"],
                        "source": row["source"],
                        "metadata": json.loads(row["metadata"]),
                    }
                    for row in rows
                ]
    except Exception as exc:  # noqa: BLE001
        logger.warning("DB search failed (table may be empty): %s", exc)
        return []


async def count_chunks(domain: str | None = None) -> int:
    """Return total knowledge chunks, optionally filtered by domain."""
    sql = "SELECT COUNT(*) FROM knowledge_chunks"
    params: list[str] = []
    if domain:
        sql += " WHERE domain = ?"
        params.append(domain)

    try:
        async with aiosqlite.connect(_DB_PATH) as conn:
            async with conn.execute(sql, params) as cursor:
                row = await cursor.fetchone()
                return int(row[0]) if row else 0
    except Exception:  # noqa: BLE001
        return 0
