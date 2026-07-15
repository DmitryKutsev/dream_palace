from typing import Any

import pytest

from dream_palace.agents import Orchestrator
from dream_palace.shared.domain import IncomingMessage, Intent, UserContext


class FakeStore:
    def __init__(self, approved: set[int]) -> None:
        self.approved = approved
        self.saved: list[tuple[int, IncomingMessage]] = []
        self.dreams: dict[int, list[dict[str, Any]]] = {}

    def is_approved(self, context: UserContext) -> bool:
        return context.telegram_id in self.approved

    def save_dream(self, context: UserContext, message: IncomingMessage) -> str:
        assert context.telegram_id == message.telegram_id
        self.saved.append((context.telegram_id, message))
        return "dream-1"

    def list_dreams(self, context: UserContext) -> list[dict[str, Any]]:
        return self.dreams.get(context.telegram_id, [])


@pytest.mark.parametrize("text", [None, "", "maybe showish", "I was flying", "analyseish"])
def test_ambiguous_input_defaults_to_dream(text: str | None) -> None:
    assert Orchestrator.classify(text) is Intent.DREAM


def test_explicit_intents() -> None:
    assert Orchestrator.classify("analyse my last dream") is Intent.ANALYSE
    assert Orchestrator.classify("show my dreams") is Intent.RETRIEVE


def test_unapproved_user_is_rejected() -> None:
    with pytest.raises(PermissionError):
        Orchestrator(FakeStore(set())).handle(IncomingMessage(telegram_id=42, text="a dream"))


def test_active_user_id_is_used_for_storage() -> None:
    store = FakeStore({42})
    result = Orchestrator(store).handle(IncomingMessage(telegram_id=42, text="a dream"))
    assert result["dream_id"] == "dream-1"
    assert store.saved[0][0] == 42


def test_retrieval_cannot_cross_user_boundary() -> None:
    store = FakeStore({42})
    store.dreams[7] = [{"text": "another user's dream"}]
    result = Orchestrator(store).handle(IncomingMessage(telegram_id=42, text="show my dreams"))
    assert result["dreams"] == []
