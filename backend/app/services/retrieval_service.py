import json
from pathlib import Path

from app.agents.registry import AgentConfig
from app.models.knowledge import KnowledgeDocument


class RetrievalService:
    """
    Knowledge retrieval boundary.

    Today this loads lightweight local JSON files when present. Later this
    class can delegate to Supabase, embeddings, vector search, official
    government sources, or a hybrid retriever without changing the agent layer.
    """

    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = data_dir or Path(__file__).resolve().parents[2] / "data"

    async def retrieve(
        self,
        *,
        agent: AgentConfig,
        query: str,
        limit: int = 4,
    ) -> list[KnowledgeDocument]:
        documents = self._load_domain_documents(agent.knowledge_domain)

        if not documents:
            return []

        query_terms = {
            term.lower()
            for term in query.replace("?", " ").replace(",", " ").split()
            if len(term) > 2
        }

        scored: list[tuple[int, KnowledgeDocument]] = []

        for document in documents:
            haystack = f"{document.title} {document.content}".lower()
            score = sum(1 for term in query_terms if term in haystack)
            if score > 0:
                scored.append((score, document))

        if not scored:
            return documents[:limit]

        scored.sort(key=lambda item: item[0], reverse=True)
        return [document for _, document in scored[:limit]]

    def format_context(self, documents: list[KnowledgeDocument]) -> str:
        if not documents:
            return "No verified local knowledge matched this query."

        blocks = []
        for index, document in enumerate(documents, start=1):
            blocks.append(
                "\n".join(
                    [
                        f"[{index}] {document.title}",
                        f"Source: {document.source}",
                        document.content,
                    ]
                )
            )

        return "\n\n".join(blocks)

    def serialize(
        self,
        documents: list[KnowledgeDocument],
    ) -> list[dict]:
        return [
            {
                "id": document.id,
                "domain": document.domain,
                "title": document.title,
                "source": document.source,
                "metadata": document.metadata,
            }
            for document in documents
        ]

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
                continue

            documents.extend(
                self._normalize_json(
                    raw=raw,
                    domain=domain,
                    source=file_path.name,
                )
            )

        return documents

    def _normalize_json(
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
                    id=f"{domain}:{source}:{index}",
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


retrieval_service = RetrievalService()
