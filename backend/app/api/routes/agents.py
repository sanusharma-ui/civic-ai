from fastapi import APIRouter, HTTPException

from app.agents.registry import get_agent, list_agents
from app.schemas.agent import AgentRead


router = APIRouter()


def _to_agent_read(agent) -> AgentRead:
    return AgentRead(
        id=agent.agent_id,
        name=agent.name,
        description=agent.description,
        knowledge_domain=agent.knowledge_domain,
        version=agent.version,
    )


@router.get("", response_model=list[AgentRead])
async def get_agents() -> list[AgentRead]:
    return [_to_agent_read(agent) for agent in list_agents()]


@router.get("/{agent_id}", response_model=AgentRead)
async def get_agent_by_id(agent_id: str) -> AgentRead:
    try:
        return _to_agent_read(get_agent(agent_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
