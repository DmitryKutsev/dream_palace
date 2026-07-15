from google.adk.agents import Agent

from dream_palace.agents.prompts import ORCHESTRATOR_INSTRUCTION


def build_agent(model: str) -> Agent:
    return Agent(
        name="dream_orchestrator",
        model=model,
        description="Routes private dream journal messages.",
        instruction=ORCHESTRATOR_INSTRUCTION,
    )
