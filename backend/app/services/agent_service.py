"""
Agent Orchestration Service — ReAct Agentic Loop.

This is the brain of the system. For every user message, it:

1. Builds the initial message list (system prompt + context + history + user).
2. Calls Groq with the agent's tool schemas (generate_with_tools).
3. If the LLM requests tool calls → executes them via ToolRunner → injects
   tool results → calls Groq again.
4. Repeats up to MAX_ITERATIONS times.
5. Parses the final text response into structured canvas blocks.
6. Returns a normalised response dict.

For streaming, the agentic loop runs first (non-streaming), then the
structured result is emitted block-by-block as SSE events.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from app.agents.registry import AgentConfig, get_agent
from app.core.config import settings
from app.schemas.chat import StructuredBlock
from app.services.groq_service import groq_service
from app.services.retrieval_service import retrieval_service
from app.services.tools_service import TOOL_SCHEMAS, ToolRunner
from app.utils.text import parse_structured_response

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 5  # max tool-call rounds before forcing a final answer


# ---------------------------------------------------------------------------
# AgentService
# ---------------------------------------------------------------------------


class AgentService:
    """
    Orchestrates the full agentic reasoning loop for any registered agent.

    Public interface:
    - ``respond()``         → full response dict (non-streaming)
    - ``stream_response()`` → async iterator of SSE-ready dicts
    """

    # ------------------------------------------------------------------
    # Non-streaming (primary path)
    # ------------------------------------------------------------------

    async def respond(
        self,
        *,
        agent_id: str,
        user_message: str,
        conversation_history: list[dict[str, str]] | None = None,
        verified_context: str | None = None,
    ) -> dict[str, Any]:
        """
        Run the full ReAct loop and return a structured response.

        Returns
        -------
        dict with keys:
          - agent        : {id, name, version}
          - response     : str  (raw LLM text — fallback)
          - structured   : list[dict]  (canvas blocks)
          - model        : str
          - usage        : dict | None
        """
        agent = get_agent(agent_id)
        tool_runner = ToolRunner(retrieval_service=retrieval_service, agent=agent)

        # Initial search: prime the context with relevant knowledge before loop
        initial_docs = await retrieval_service.retrieve(agent=agent, query=user_message)
        init_context = retrieval_service.format_context(initial_docs)

        messages = self._build_initial_messages(
            agent=agent,
            user_message=user_message,
            conversation_history=conversation_history,
            verified_context=verified_context or init_context,
        )

        final_content = ""
        final_usage: dict | None = None
        final_model = settings.groq_model

        for iteration in range(MAX_ITERATIONS):
            logger.info(
                "Agent loop iteration %d/%d for agent '%s'",
                iteration + 1,
                MAX_ITERATIONS,
                agent_id,
            )

            result = await groq_service.generate_with_tools(
                messages=messages,
                tools=TOOL_SCHEMAS,
                temperature=settings.groq_temperature,
                max_tokens=settings.groq_max_tokens,
            )

            final_model = result.get("model", final_model)
            if result.get("usage"):
                final_usage = result["usage"]

            tool_calls = result.get("tool_calls")

            # --- Final answer (no tool calls requested) ---
            if not tool_calls:
                final_content = result.get("content", "")
                break

            # --- Execute tool calls ---
            # Append the assistant's tool-call message first
            messages.append(
                {
                    "role": "assistant",
                    "content": result.get("content") or "",
                    "tool_calls": [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": json.dumps(tc["arguments"]),
                            },
                        }
                        for tc in tool_calls
                    ],
                }
            )

            # Execute each tool and append its result
            for tc in tool_calls:
                observation = await tool_runner.run(
                    tool_name=tc["name"],
                    tool_args=tc["arguments"],
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": observation,
                    }
                )

            # Last iteration — force a final answer
            if iteration == MAX_ITERATIONS - 1:
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Based on all the information gathered above, "
                            "please provide your complete structured response now. "
                            "Remember to wrap it in <structured_response> tags."
                        ),
                    }
                )
                final_result = await groq_service.generate(
                    messages=messages,
                    temperature=settings.groq_temperature,
                    max_tokens=settings.groq_max_tokens,
                )
                final_content = final_result.get("content", "")
                final_usage = final_result.get("usage") or final_usage
                break

        # Parse structured blocks from final content
        structured_blocks = parse_structured_response(final_content)
        structured = [StructuredBlock(**block) for block in structured_blocks]

        return {
            "agent": {
                "id": agent.agent_id,
                "name": agent.name,
                "version": agent.version,
            },
            "response": final_content,
            "structured": structured,
            "model": final_model,
            "usage": final_usage,
            "retrieved_context": retrieval_service.serialize(initial_docs),
        }

    # ------------------------------------------------------------------
    # Streaming (SSE path)
    # ------------------------------------------------------------------

    async def stream_response(
        self,
        *,
        agent_id: str,
        user_message: str,
        conversation_history: list[dict[str, str]] | None = None,
        verified_context: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Run the agentic loop, then yield structured blocks as SSE events.

        Yields dicts (not raw strings) — the route serialises to JSON.

        Event sequence:
        1. ``thinking`` — agent loop is running (optional UI spinner)
        2. ``block``    — one event per structured block
        3. ``done``     — final summary
        4. ``error``    — if something goes wrong
        """
        try:
            yield {"type": "thinking", "message": "Analysing your request…"}

            result = await self.respond(
                agent_id=agent_id,
                user_message=user_message,
                conversation_history=conversation_history,
                verified_context=verified_context,
            )

            # Emit each block as a separate event
            for block in result["structured"]:
                yield {
                    "type": "block",
                    "block": block.model_dump(),
                }

            yield {
                "type": "done",
                "agent": result["agent"],
                "model": result["model"],
                "usage": result["usage"],
                "retrieved_context": result["retrieved_context"],
                "response": result["response"],
            }

        except Exception as exc:  # noqa: BLE001
            logger.error("stream_response error: %s", exc, exc_info=True)
            yield {
                "type": "error",
                "detail": str(exc),
            }

    # ------------------------------------------------------------------
    # Message builders
    # ------------------------------------------------------------------

    def _build_initial_messages(
        self,
        *,
        agent: AgentConfig,
        user_message: str,
        conversation_history: list[dict[str, str]] | None,
        verified_context: str,
    ) -> list[dict[str, Any]]:
        """Construct the full messages list for the first loop iteration."""
        system_prompt = self._build_system_prompt(
            agent=agent,
            verified_context=verified_context,
        )

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt}
        ]

        if conversation_history:
            messages.extend(self._sanitize_history(conversation_history))

        messages.append({"role": "user", "content": user_message})
        return messages

    @staticmethod
    def _build_system_prompt(
        *,
        agent: AgentConfig,
        verified_context: str,
    ) -> str:
        context_block = verified_context or "No verified external knowledge has been provided."

        return f"""{agent.system_prompt}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AGENT IDENTITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Name   : {agent.name}
Domain : {agent.knowledge_domain}
Purpose: {agent.description}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PRE-LOADED VERIFIED KNOWLEDGE CONTEXT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The following knowledge was retrieved for this query.
Use it as your primary source. Call search_knowledge for more.

{context_block}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REMEMBER: Your ENTIRE final response must be inside <structured_response> tags.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━""".strip()

    @staticmethod
    def _sanitize_history(
        history: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        """Strip non-user/assistant messages from client-supplied history."""
        sanitized: list[dict[str, str]] = []
        for message in history:
            role = message.get("role")
            content = message.get("content")
            if role not in {"user", "assistant"}:
                continue
            if not content:
                continue
            sanitized.append({"role": role, "content": content})
        return sanitized


agent_service = AgentService()
