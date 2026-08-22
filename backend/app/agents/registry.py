from dataclasses import dataclass
from typing import Dict

from app.prompts.consumer import CONSUMER_SYSTEM_PROMPT
from app.prompts.rti import RTI_SYSTEM_PROMPT


@dataclass(frozen=True)
class AgentConfig:
    """
    Immutable configuration for a specialized civic agent.

    The actual prompts will be added in the next stage.
    """

    agent_id: str
    name: str
    description: str
    knowledge_domain: str
    system_prompt: str
    version: str = "1.0"


AGENTS: Dict[str, AgentConfig] = {
    "rti": AgentConfig(
        agent_id="rti",
        name="RTI Agent",
        description=(
            "Helps citizens understand and prepare "
            "Right to Information requests."
        ),
        knowledge_domain="rti",
        system_prompt=RTI_SYSTEM_PROMPT,
    ),

    "consumer": AgentConfig(
        agent_id="consumer",
        name="Consumer Rights Agent",
        description=(
            "Helps citizens understand consumer rights, "
            "complaints and available remedies."
        ),
        knowledge_domain="consumer",
        system_prompt=CONSUMER_SYSTEM_PROMPT,
    ),
}


def get_agent(agent_id: str) -> AgentConfig:
    """
    Return the configuration for a requested agent.

    Raises:
        ValueError: If the requested agent does not exist.
    """

    agent = AGENTS.get(agent_id)

    if agent is None:
        raise ValueError(
            f"Unknown agent '{agent_id}'. "
            f"Available agents: {list(AGENTS.keys())}"
        )

    return agent


def list_agents() -> list[AgentConfig]:
    """Return all available agents."""

    return list(AGENTS.values())
