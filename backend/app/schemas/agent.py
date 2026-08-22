"""Pydantic schemas for agent metadata."""

from pydantic import BaseModel


class AgentRead(BaseModel):
    id: str
    name: str
    description: str
    knowledge_domain: str
    version: str
    capabilities: list[str] = []
    example_questions: list[str] = []
