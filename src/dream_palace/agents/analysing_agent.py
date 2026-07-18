"""Per-user dream analysis agent.

The agent's only tool closes over an authenticated ``UserContext``, so the
model never chooses (and can never change) whose dreams it reads: the tenant
boundary is enforced in Python, not in the prompt.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types

from dream_palace.agents.prompts.analyst import ANALYST_INSTRUCTION
from dream_palace.shared.domain import UserContext
from dream_palace.tools.dream_store import DreamStore


def build_analysing_agent(model: str, store: DreamStore, context: UserContext) -> Agent:
    def list_my_dreams(days: int = 30, limit: int = 50) -> list[dict[str, Any]]:
        """Return the current user's dreams from the last `days` days, newest first."""
        since = datetime.now(UTC) - timedelta(days=days)
        return [
            {
                "id": dream.get("id"),
                "text": dream.get("text"),
                "received_at": str(dream.get("received_at")),
            }
            for dream in store.list_dreams(context, since=since, limit=limit)
        ]

    return Agent(
        name="dream_analyst",
        model=model,
        description="Analyses a single user's dream journal for recurring themes.",
        instruction=ANALYST_INSTRUCTION,
        tools=[list_my_dreams],
    )


async def run_analysis(
    model: str, store: DreamStore, context: UserContext, question: str
) -> str:
    agent = build_analysing_agent(model, store, context)
    runner = InMemoryRunner(agent=agent)
    session = await runner.session_service.create_session(
        app_name=runner.app_name, user_id=str(context.telegram_id)
    )
    message = types.Content(role="user", parts=[types.Part(text=question)])
    reply: list[str] = []
    async for event in runner.run_async(
        user_id=str(context.telegram_id), session_id=session.id, new_message=message
    ):
        if event.is_final_response() and event.content and event.content.parts:
            reply.extend(part.text for part in event.content.parts if part.text)
    return "\n".join(reply)
