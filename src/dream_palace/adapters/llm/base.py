"""Abstract LLM adapter so agents are not welded to a single provider."""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel


class LLMConfig(BaseModel):
    model_name: str
    api_key: str = ""
    temperature: float = 0.2
    max_tokens: int = 2048


class LLMAdapter(ABC):
    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    @abstractmethod
    async def complete(self, prompt: str, system: str | None = None) -> str: ...
