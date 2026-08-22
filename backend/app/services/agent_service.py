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

For streaming, the service uses the retrieved knowledge context and emits
model tokens directly, so the UI can start printing as soon as the model
begins answering.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
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
        Stream a markdown answer as model tokens.

        Yields dicts (not raw strings) — the route serialises to JSON.

        Event sequence:
        1. ``thinking`` — context retrieval is running (optional UI hint)
        2. ``token``    — incremental markdown text
        3. ``done``     — final summary
        4. ``error``    — if something goes wrong
        """
        try:
            yield {"type": "thinking", "message": "Analysing your request..."}

            agent = get_agent(agent_id)

            local_response = self._local_streaming_response(
                agent=agent,
                user_message=user_message,
            )
            if local_response:
                async for token in self._stream_text(local_response):
                    yield {"type": "token", "token": token}
                yield {
                    "type": "done",
                    "agent": {
                        "id": agent.agent_id,
                        "name": agent.name,
                        "version": agent.version,
                    },
                    "model": "local",
                    "usage": None,
                    "retrieved_context": [],
                    "response": local_response,
                    "structured": [],
                }
                return

            initial_docs = await retrieval_service.retrieve(agent=agent, query=user_message)
            init_context = retrieval_service.format_context(initial_docs)
            messages = self._build_streaming_messages(
                agent=agent,
                user_message=user_message,
                conversation_history=conversation_history,
                verified_context=verified_context or init_context,
            )

            full_response = ""
            try:
                async with asyncio.timeout(60):
                    async for token in groq_service.stream(
                        messages=messages,
                        temperature=settings.groq_temperature,
                        max_tokens=settings.groq_max_tokens,
                    ):
                        full_response += token
                        yield {"type": "token", "token": token}
            except TimeoutError:
                if not full_response:
                    full_response = (
                        "I could not get a response from the AI model in time. "
                        "Please try again in a moment."
                    )
                    async for token in self._stream_text(full_response):
                        yield {"type": "token", "token": token}

            structured_blocks = (
                parse_structured_response(full_response)
                if "<structured_response" in full_response.lower()
                else []
            )
            structured = [StructuredBlock(**block) for block in structured_blocks]

            yield {
                "type": "done",
                "agent": {
                    "id": agent.agent_id,
                    "name": agent.name,
                    "version": agent.version,
                },
                "model": settings.groq_model,
                "usage": None,
                "retrieved_context": retrieval_service.serialize(initial_docs),
                "response": full_response,
                "structured": structured,
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

    def _build_streaming_messages(
        self,
        *,
        agent: AgentConfig,
        user_message: str,
        conversation_history: list[dict[str, str]] | None,
        verified_context: str,
    ) -> list[dict[str, Any]]:
        """Construct messages for direct markdown streaming."""
        context_block = verified_context or "No verified external knowledge has been provided."
        system_prompt = f"""You are {agent.name} for Civic AI.

RESPONSE FORMAT
- Return clean GitHub-Flavored Markdown directly.
- Never wrap the answer in <structured_response> tags.
- Never return the internal structured JSON response shape.
- Do not output JSON unless the user explicitly asks for JSON.
- Use short headings, bullet lists, numbered steps, and markdown tables where they improve clarity.
- Put drafts, notices, applications, examples, and code-like templates in fenced code blocks with a useful language label such as text or markdown.
- Keep the answer professional, practical, and easy to scan.

BEHAVIOUR
- Be practical, calm, and citizen-friendly.
- Ask for missing details when a complete RTI/application/notice cannot be drafted yet.
- Stay within this agent's domain. If the user asks outside the domain, redirect briefly.
- Mention that this is AI-generated guidance when giving legal/procedural guidance.

CONVERSATIONAL FORM-FILLER PROTOCOL
When the user's intent is to draft an RTI application, consumer complaint, legal notice, or any official form:
1. Do NOT generate the form immediately. First, identify ALL required fields that are missing.
2. Ask for ONE or TWO missing fields at a time in a friendly, conversational way. Required fields depend on the form type:
   - RTI Application: department/public authority, specific information sought, government level (central/state), applicant name, applicant address
   - Consumer Complaint: seller/company name, product or service, nature of defect, purchase date, amount paid, what resolution is demanded
3. After each user reply, acknowledge the information provided and ask for the next missing field(s).
4. Once you have ALL required details, generate the complete, ready-to-use form inside a fenced code block labeled `text`.
5. After presenting the draft, say: "You can copy this and submit it. Want me to change anything — like a name, date, or specific wording?"
6. If the user already provides most details upfront in a single message, skip ahead — only ask about what is genuinely missing.
7. Never produce a form with placeholder brackets like [Your Name] if the user has already provided that information in the conversation.

AGENT IDENTITY
Name   : {agent.name}
Domain : {agent.knowledge_domain}
Purpose: {agent.description}

PRE-LOADED VERIFIED KNOWLEDGE CONTEXT
Use this as your primary source. If something is not covered, say so clearly and give cautious general guidance.

{context_block}
""".strip()

        messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        if conversation_history:
            messages.extend(self._sanitize_history(conversation_history))
        messages.append({"role": "user", "content": user_message})
        return messages

    @staticmethod
    async def _stream_text(text: str) -> AsyncIterator[str]:
        """Yield small chunks so local/fallback responses also type smoothly."""
        for chunk in re.findall(r"\S+\s*", text):
            yield chunk
            await asyncio.sleep(0.018)

    @staticmethod
    def _local_streaming_response(*, agent: AgentConfig, user_message: str) -> str | None:
        """Fast-path tiny greetings instead of waiting on the model."""
        normalized = re.sub(r"[^a-zA-Z\s]", "", user_message).strip().lower()
        greetings = {
            "hi",
            "hello",
            "hey",
            "hii",
            "hiii",
            "namaste",
            "namaskar",
            "bhai",
            "hello agent",
            "hi agent",
        }
        if normalized not in greetings:
            return None

        if agent.agent_id == "consumer":
            return (
                "### Hello\n\n"
                "I am ready to help with consumer rights, refunds, defective products, "
                "service complaints, legal notices, and consumer court filing.\n\n"
                "Tell me what happened, the company/seller name, purchase date, amount, "
                "and what resolution you want."
            )

        return (
            "### Hello\n\n"
            "I am ready to help with RTI questions, public authority selection, RTI drafts, "
            "first appeals, and timelines.\n\n"
            "Tell me what information you need, which department is involved, and any "
            "reference number or date you already have."
        )

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
            if role == "assistant" and "<structured_response" in content.lower():
                blocks = parse_structured_response(content)
                content = "\n\n".join(
                    (
                        f"{block['title']}\n{block['content']}"
                        if block.get("title")
                        else block.get("content", "")
                    ).strip()
                    for block in blocks
                    if block.get("content")
                )
            if content.strip().lower() in {"_thinking..._", "thinking..."}:
                continue
            sanitized.append({"role": role, "content": content})
        return sanitized


agent_service = AgentService()
