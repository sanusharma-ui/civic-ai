from dataclasses import dataclass


@dataclass(frozen=True)
class KnowledgeDocument:
    id: str
    domain: str
    title: str
    content: str
    source: str
    metadata: dict
