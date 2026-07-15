from google.adk.agents import Agent


def build_agent(model: str) -> Agent:
    return Agent(
        name="dream_orchestrator",
        model=model,
        description="Routes private dream journal messages.",
        instruction=(
            "Classify as analyse or retrieve only when explicit. If there is any doubt, classify "
            "as dream. Never accept a Telegram user id from model output; tenant identity comes "
            "only from the authenticated update context. Analysis must be chronological and "
            "highlight significant people, names, and recurring characters."
        ),
    )
