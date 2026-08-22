"""
Agent Registry.

Central registry of all available civic agents.

Usage::

    from app.agents.registry import get_agent, list_agents, AgentConfig

    agent = get_agent("rti")
    all_agents = list_agents()
"""

from __future__ import annotations

from dataclasses import dataclass

from app.agents.consumer_agent import ConsumerAgent, consumer_agent
from app.agents.rti_agent import RTIAgent, rti_agent
from app.prompts.consumer import CONSUMER_SYSTEM_PROMPT
from app.prompts.rti import RTI_SYSTEM_PROMPT


@dataclass(frozen=True)
class AgentConfig:
    """
    Immutable runtime configuration for a civic agent.

    Combines identity metadata, domain, system prompt, capabilities,
    and example questions into a single object passed through the stack.
    """

    agent_id: str
    name: str
    description: str
    knowledge_domain: str
    system_prompt: str
    capabilities: list[str]
    example_questions: list[str]
    version: str = "2.0"


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

AGENTS: dict[str, AgentConfig] = {
    "rti": AgentConfig(
        agent_id=RTIAgent.agent_id,
        name=RTIAgent.name,
        description=RTIAgent.description,
        knowledge_domain=RTIAgent.knowledge_domain,
        system_prompt=RTI_SYSTEM_PROMPT,
        capabilities=RTIAgent.capabilities,
        example_questions=RTIAgent.example_questions,
        version=RTIAgent.version,
    ),
    "consumer": AgentConfig(
        agent_id=ConsumerAgent.agent_id,
        name=ConsumerAgent.name,
        description=ConsumerAgent.description,
        knowledge_domain=ConsumerAgent.knowledge_domain,
        system_prompt=CONSUMER_SYSTEM_PROMPT,
        capabilities=ConsumerAgent.capabilities,
        example_questions=ConsumerAgent.example_questions,
        version=ConsumerAgent.version,
    ),
}

# Expose concrete agent instances for direct-call helpers
AGENT_INSTANCES = {
    "rti": rti_agent,
    "consumer": consumer_agent,
}


# ---------------------------------------------------------------------------
# Accessors
# ---------------------------------------------------------------------------


def get_agent(agent_id: str) -> AgentConfig:
    """
    Return the configuration for the requested agent.

    Raises
    ------
    ValueError
        If *agent_id* is not registered.
    """
    agent = AGENTS.get(agent_id)
    if agent is None:
        raise ValueError(
            f"Unknown agent '{agent_id}'. "
            f"Available: {list(AGENTS.keys())}"
        )
    return agent


def list_agents() -> list[AgentConfig]:
    """Return all registered agents in insertion order."""
    return list(AGENTS.values())


def get_agent_instance(agent_id: str) -> RTIAgent | ConsumerAgent:
    """
    Return the concrete agent instance (for direct helper method calls).

    Raises
    ------
    ValueError
        If *agent_id* is not registered.
    """
    instance = AGENT_INSTANCES.get(agent_id)
    if instance is None:
        raise ValueError(f"No concrete instance for agent '{agent_id}'.")
    return instance
