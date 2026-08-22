import argparse
import asyncio
import sys
from pathlib import Path

# Allow running this script directly from backend/scripts.
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.agents.registry import get_agent, list_agents
from app.services.agent_service import agent_service
from app.services.chat_service import chat_service
from app.services.groq_service import GroqServiceError
from app.services.retrieval_service import retrieval_service


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Interactive CLI chat for Civic AI agents."
    )
    parser.add_argument(
        "--agent",
        default="rti",
        help="Agent id to start with (rti or consumer).",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Stream tokens while generating response.",
    )
    return parser


def _available_agents_text() -> str:
    return ", ".join(agent.agent_id for agent in list_agents())


def _history_for_llm(conversation_id: str) -> list[dict[str, str]]:
    conversation = chat_service.get_conversation(conversation_id)
    return [
        {"role": message.role, "content": message.content}
        for message in conversation.messages[-12:]
    ]


async def _ask_once(
    *,
    agent_id: str,
    conversation_id: str,
    user_message: str,
    stream: bool,
) -> str:
    agent = get_agent(agent_id)
    history = _history_for_llm(conversation_id)
    documents = await retrieval_service.retrieve(
        agent=agent,
        query=user_message,
    )
    verified_context = retrieval_service.format_context(documents)

    if stream:
        parts: list[str] = []
        async for token in agent_service.stream_response(
            agent_id=agent_id,
            user_message=user_message,
            conversation_history=history,
            verified_context=verified_context,
        ):
            parts.append(token)
            print(token, end="", flush=True)
        print()
        return "".join(parts)

    result = await agent_service.respond(
        agent_id=agent_id,
        user_message=user_message,
        conversation_history=history,
        verified_context=verified_context,
    )
    print(result["response"])
    return result["response"]


async def _run_cli(agent_id: str, stream: bool) -> None:
    get_agent(agent_id)

    conversation = chat_service.create_conversation(agent_id=agent_id)

    print("Civic AI CLI")
    print(f"Active agent: {agent_id}")
    print(f"Available agents: {_available_agents_text()}")
    print("Commands: /agent <id>, /new, /id, /help, /exit")

    while True:
        try:
            user_message = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            return

        if not user_message:
            continue

        if user_message in {"/exit", "/quit"}:
            print("Exiting.")
            return

        if user_message == "/help":
            print("Commands: /agent <id>, /new, /id, /help, /exit")
            continue

        if user_message == "/id":
            print(f"Conversation ID: {conversation.id}")
            continue

        if user_message == "/new":
            conversation = chat_service.create_conversation(agent_id=agent_id)
            print(f"Started new conversation: {conversation.id}")
            continue

        if user_message.startswith("/agent "):
            next_agent = user_message.split(maxsplit=1)[1].strip()
            try:
                get_agent(next_agent)
            except ValueError as exc:
                print(str(exc))
                continue

            agent_id = next_agent
            conversation = chat_service.create_conversation(agent_id=agent_id)
            print(f"Switched to agent '{agent_id}'")
            print(f"Conversation ID: {conversation.id}")
            continue

        try:
            answer = await _ask_once(
                agent_id=agent_id,
                conversation_id=conversation.id,
                user_message=user_message,
                stream=stream,
            )
            conversation.add_message("user", user_message)
            conversation.add_message("assistant", answer)
        except (ValueError, GroqServiceError) as exc:
            print(f"Error: {exc}")


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    try:
        asyncio.run(_run_cli(agent_id=args.agent, stream=args.stream))
    except ValueError as exc:
        print(f"Error: {exc}")


if __name__ == "__main__":
    main()
