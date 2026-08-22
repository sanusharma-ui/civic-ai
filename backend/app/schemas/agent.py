from pydantic import BaseModel


class AgentRead(BaseModel):
    id: str
    name: str
    description: str
    knowledge_domain: str
    version: str
