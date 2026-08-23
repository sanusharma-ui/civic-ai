"""
Knowledge retrieval service.

Retrieves relevant knowledge from:
1. Local JSON files in the data/ directory (seed knowledge, always works).
2. SQLite database (populated later via admin/ingestion scripts).

Both sources are merged and deduplicated. The interface is kept stable
so that adding vector search / Supabase later only changes this module.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

from app.agents.registry import AgentConfig
from app.models.knowledge import KnowledgeDocument

logger = logging.getLogger(__name__)


class RetrievalService:
    """
    Retrieves knowledge documents relevant to a user query.

    Priority: JSON files (always available) + DB results (when populated).
    Results are keyword-scored and returned best-match first.
    """

    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = data_dir or Path(__file__).resolve().parents[2] / "data"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def retrieve(
        self,
        *,
        agent: AgentConfig,
        query: str,
        limit: int = 5,
    ) -> list[KnowledgeDocument]:
        """
        Retrieve the most relevant documents for *query* in *agent.knowledge_domain*.

        Sources searched (in order, results merged):
        1. JSON seed files in data/<domain>/
        2. SQLite database (gracefully skipped if empty)
        """
        domain = agent.knowledge_domain

        # Gather from both sources
        json_docs = self._load_domain_documents(domain)
        db_docs = await self._search_db(domain=domain, query=query, limit=limit)

        # Merge, deduplicate by id
        seen_ids: set[str] = set()
        all_docs: list[KnowledgeDocument] = []
        for doc in (*db_docs, *json_docs):  # DB first (more authoritative when populated)
            if doc.id not in seen_ids:
                seen_ids.add(doc.id)
                all_docs.append(doc)

        if not all_docs:
            return []

        # Score by keyword overlap with query
        return self._score_and_rank(all_docs, query=query, limit=limit)

    def format_context(self, documents: list[KnowledgeDocument], max_chars: int = 12000) -> str:
        """Format documents as a numbered context block for LLM injection."""
        if not documents:
            return (
                "No verified knowledge matched this query. "
                "Use your trained knowledge and clearly note that you are doing so."
            )

        blocks = []
        for index, doc in enumerate(documents, start=1):
            blocks.append(
                "\n".join(
                    [
                        f"[{index}] {doc.title}",
                        f"Source: {doc.source}",
                        f"Domain: {doc.domain}",
                        doc.content,
                    ]
                )
            )
        return "\n\n".join(blocks)[:max_chars]

    def serialize(self, documents: list[KnowledgeDocument]) -> list[dict]:
        """Serialise documents for API response (no full content — just metadata)."""
        return [
            {
                "id": doc.id,
                "domain": doc.domain,
                "title": doc.title,
                "source": doc.source,
                "metadata": doc.metadata,
            }
            for doc in documents
        ]

    # ------------------------------------------------------------------
    # Private — JSON files
    # ------------------------------------------------------------------

    @lru_cache(maxsize=8)
    def _load_domain_documents(self, domain: str) -> list[KnowledgeDocument]:
        domain_dir = self.data_dir / domain
        if not domain_dir.exists():
            return []

        documents: list[KnowledgeDocument] = []
        for file_path in sorted(domain_dir.glob("*.json")):
            if file_path.stat().st_size == 0:
                continue
            try:
                raw = json.loads(file_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                logger.warning("Invalid JSON in %s — skipped", file_path)
                continue
            documents.extend(
                self._normalise_json(raw=raw, domain=domain, source=file_path.name)
            )

        return documents

    def _normalise_json(
        self,
        *,
        raw: object,
        domain: str,
        source: str,
    ) -> list[KnowledgeDocument]:
        items = raw if isinstance(raw, list) else [raw]
        documents: list[KnowledgeDocument] = []

        for index, item in enumerate(items):
            if not isinstance(item, dict):
                continue

            title = str(
                item.get("title")
                or item.get("question")
                or item.get("section")
                or f"{source} item {index + 1}"
            )
            content = str(
                item.get("content")
                or item.get("answer")
                or item.get("text")
                or item
            )

            documents.append(
                KnowledgeDocument(
                    id=f"json:{domain}:{source}:{index}",
                    domain=domain,
                    title=title,
                    content=content,
                    source=source,
                    metadata={
                        key: value
                        for key, value in item.items()
                        if key not in {"title", "question", "content", "answer", "text"}
                    },
                )
            )

        return documents

    # ------------------------------------------------------------------
    # Private — Database
    # ------------------------------------------------------------------

    async def _search_db(
        self,
        *,
        domain: str,
        query: str,
        limit: int,
    ) -> list[KnowledgeDocument]:
        """Search the SQLite database. Returns empty list gracefully if unavailable."""
        try:
            from app.core.database import search_chunks

            rows = await search_chunks(domain=domain, query=query, limit=limit)
            return [
                KnowledgeDocument(
                    id=f"db:{row['id']}",
                    domain=row["domain"],
                    title=row["title"],
                    content=row["content"],
                    source=row["source"],
                    metadata=row.get("metadata", {}),
                )
                for row in rows
            ]
        except Exception as exc:  # noqa: BLE001
            logger.debug("DB retrieval skipped: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Private — Scoring
    # ------------------------------------------------------------------

    def _score_and_rank(
        self,
        documents: list[KnowledgeDocument],
        *,
        query: str,
        limit: int,
    ) -> list[KnowledgeDocument]:
        """Simple TF-overlap ranking."""
        query_terms = {
            term.lower()
            for term in query.replace("?", " ").replace(",", " ").split()
            if len(term) > 2
        }

        if not query_terms:
            return documents[:limit]

        scored: list[tuple[int, KnowledgeDocument]] = []
        for doc in documents:
            haystack = f"{doc.title} {doc.content}".lower()
            score = sum(1 for term in query_terms if term in haystack)
            scored.append((score, doc))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [doc for _, doc in scored[:limit]]


retrieval_service = RetrievalService()
