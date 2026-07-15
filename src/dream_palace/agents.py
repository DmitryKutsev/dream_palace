from __future__ import annotations

from collections import Counter
from typing import Any

from dream_palace.domain import IncomingMessage, Intent, UserContext
from dream_palace.storage import DreamStore


class Orchestrator:
    """Safe routing boundary around ADK agents and tenant-scoped tools."""

    def __init__(self, store: DreamStore) -> None:
        self.store = store

    @staticmethod
    def classify(text: str | None) -> Intent:
        normalized = (text or "").strip().lower()
        if normalized.startswith(("analyse ", "analyze ", "/analyse", "/analyze")):
            return Intent.ANALYSE
        if normalized.startswith(("show ", "get ", "find ", "/dreams")):
            return Intent.RETRIEVE
        return Intent.DREAM

    def handle(self, message: IncomingMessage) -> dict[str, Any]:
        context = UserContext(telegram_id=message.telegram_id)
        if not self.store.is_approved(context):
            raise PermissionError("user is not approved")
        intent = self.classify(message.text)
        if intent is Intent.DREAM:
            return {"intent": intent, "dream_id": self.store.save_dream(context, message)}
        dreams = self.store.list_dreams(context)
        if intent is Intent.RETRIEVE:
            return {"intent": intent, "dreams": dreams}
        return {"intent": intent, "analysis": self._analyse(dreams)}

    @staticmethod
    def _analyse(dreams: list[dict[str, Any]]) -> dict[str, Any]:
        ordered = sorted(dreams, key=lambda dream: str(dream.get("received_at", "")))
        words = [
            word.strip('.,!?"').lower()
            for dream in ordered
            for word in (dream.get("text") or "").split()
        ]
        repeated = [
            word for word, count in Counter(words).most_common() if count > 1 and len(word) > 2
        ]
        return {"chronological_dreams": ordered, "repeated_terms": repeated[:20]}
