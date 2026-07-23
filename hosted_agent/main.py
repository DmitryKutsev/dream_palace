"""Microsoft Foundry hosted Dream Palace analyst."""

import os

from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from agent_framework_foundry_hosting import ResponsesHostServer
from azure.identity import DefaultAzureCredential

INSTRUCTIONS = """\
You are the Dream Palace analyst. The calling application authenticates the
Telegram user, retrieves only that user's dreams, and gives you the resulting
journal in chronological order.

Answer only from the supplied journal. Identify recurring imagery, moods,
places, people, and changes over time. Ground observations in the entries and
use short excerpts as evidence. If no dreams are supplied, say so plainly.
Never request a Telegram ID or attempt to retrieve more records. Do not
diagnose, offer medical or psychiatric conclusions, or present symbolic
interpretations as facts.
"""


def main() -> None:
    client = FoundryChatClient(
        project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
        model=os.environ["AZURE_AI_MODEL_DEPLOYMENT_NAME"],
        credential=DefaultAzureCredential(),
    )
    agent = Agent(
        client=client,
        name="dream_analyst",
        instructions=INSTRUCTIONS,
        default_options={"store": False},
    )
    ResponsesHostServer(agent).run()


if __name__ == "__main__":
    main()
