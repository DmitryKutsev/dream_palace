"""Client boundary for the Microsoft Foundry hosted dream analyst."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from azure.ai.projects import AIProjectClient
from azure.core.credentials import TokenCredential


class AzureFoundryAnalyst:
    """Invoke a named hosted agent without giving that agent datastore credentials."""

    def __init__(
        self,
        project_endpoint: str,
        agent_name: str,
        credential: TokenCredential,
    ) -> None:
        project = AIProjectClient(endpoint=project_endpoint, credential=credential)
        self._responses = project.get_openai_client(agent_name=agent_name).responses

    async def analyse(self, question: str, dreams: list[dict[str, Any]]) -> str:
        journal = [
            {
                "id": dream.get("id"),
                "text": dream.get("text"),
                "received_at": str(dream.get("received_at")),
            }
            for dream in reversed(dreams)
        ]
        prompt = (
            "Analyse the following authenticated user's dream journal. "
            "The entries are already filtered by the application; do not request an identity "
            "or any additional records.\n\n"
            f"Question: {question}\n\n"
            f"Journal (oldest to newest):\n{json.dumps(journal, ensure_ascii=False)}"
        )
        response = await asyncio.to_thread(
            self._responses.create,
            input=prompt,
            store=False,
        )
        return response.output_text
