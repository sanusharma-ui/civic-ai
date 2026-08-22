from collections.abc import AsyncIterator
from typing import Any, Dict, List, Optional

from app.agents.registry import get_agent
from app.core.config import settings
from app.services.groq_service import groq_service


class AgentService:
    """
    Orchestrates agent behaviour.

    Responsibilities:
    - Validate/select agent
    - Build the LLM message structure
    - Inject verified context
    - Send request to Groq
    - Return normalized response

    This layer deliberately does NOT fetch legal information itself.
    Knowledge retrieval will be added as a separate service.
    """

    async def respond(
        self,
        *,
        agent_id: str,
        user_message: str,
        conversation_history: Optional[
            List[Dict[str, str]]
        ] = None,
        verified_context: Optional[str] = None,
    ) -> Dict[str, Any]:

        agent = get_agent(agent_id)

        messages: List[Dict[str, str]] = []

        system_prompt = self._build_system_prompt(
            agent=agent,
            verified_context=verified_context,
        )

        messages.append(
            {
                "role": "system",
                "content": system_prompt,
            }
        )

        if conversation_history:
            messages.extend(
                self._sanitize_history(
                    conversation_history
                )
            )

        messages.append(
            {
                "role": "user",
                "content": user_message,
            }
        )

        result = await groq_service.generate(
            messages=messages,
            temperature=settings.groq_temperature,
            max_tokens=settings.groq_max_tokens,
        )

        return {
            "agent": {
                "id": agent.agent_id,
                "name": agent.name,
                "version": agent.version,
            },
            "response": result["content"],
            "model": result["model"],
            "usage": result["usage"],
        }

    async def stream_response(
        self,
        *,
        agent_id: str,
        user_message: str,
        conversation_history: Optional[
            List[Dict[str, str]]
        ] = None,
        verified_context: Optional[str] = None,
    ) -> AsyncIterator[str]:
        agent = get_agent(agent_id)
        messages = self.build_messages(
            agent_id=agent_id,
            user_message=user_message,
            conversation_history=conversation_history,
            verified_context=verified_context,
        )

        async for token in groq_service.stream(
            messages=messages,
            temperature=settings.groq_temperature,
            max_tokens=settings.groq_max_tokens,
        ):
            yield token

    def build_messages(
        self,
        *,
        agent_id: str,
        user_message: str,
        conversation_history: Optional[
            List[Dict[str, str]]
        ] = None,
        verified_context: Optional[str] = None,
    ) -> list[dict[str, str]]:
        agent = get_agent(agent_id)

        messages: List[Dict[str, str]] = []

        messages.append(
            {
                "role": "system",
                "content": self._build_system_prompt(
                    agent=agent,
                    verified_context=verified_context,
                ),
            }
        )

        if conversation_history:
            messages.extend(self._sanitize_history(conversation_history))

        messages.append(
            {
                "role": "user",
                "content": user_message,
            }
        )

        return messages

    @staticmethod
    def _build_system_prompt(
        *,
        agent: Any,
        verified_context: Optional[str],
    ) -> str:
        """
        Construct the base system instruction.

        Specialized prompts will replace this temporary prompt
        once RTI and Consumer personas are implemented.
        """

        context_block = (
            verified_context
            if verified_context
            else "No verified external knowledge has been provided."
        )

        return f"""
{agent.system_prompt}

You are part of Civic AI. Your configured agent identity is:
- Name: {agent.name}
- Domain: {agent.knowledge_domain}
- Purpose: {agent.description}

IMPORTANT OPERATING RULES:

1. You are a civic-information assistant, not a lawyer.
2. Do not invent laws, sections, deadlines, authorities,
   fees, procedures, or legal rights.
3. Prefer verified knowledge supplied by the application.
4. If required information is unavailable, explicitly say so.
5. Never pretend that you searched the internet if no
   retrieval tool was actually used.
6. Ask concise clarification questions when the citizen's
   situation lacks important information.
7. Convert bureaucratic/legal language into simple language.
8. Focus on actionable next steps.
9. Clearly distinguish facts from suggestions.
10. When citing legal/procedural information, rely on the
    supplied verified context.

VERIFIED KNOWLEDGE CONTEXT:

---------------- BEGIN CONTEXT ----------------

{context_block}

----------------- END CONTEXT -----------------

Remember:

The application backend is responsible for retrieving
authoritative information.

You must NOT fabricate a source or claim to have fetched
information that was not supplied to you.
""".strip()

    @staticmethod
    def _sanitize_history(
        history: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """
        Keep conversation history restricted to supported
        chat roles.

        System messages from clients are intentionally ignored.
        The backend owns the system prompt.
        """

        sanitized: List[Dict[str, str]] = []

        for message in history:

            role = message.get("role")
            content = message.get("content")

            if role not in {"user", "assistant"}:
                continue

            if not content:
                continue

            sanitized.append(
                {
                    "role": role,
                    "content": content,
                }
            )

        return sanitized


agent_service = AgentService()
