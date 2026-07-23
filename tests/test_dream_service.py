from datetime import datetime
from typing import Any

import pytest

from dream_palace.service.dream_service import DreamService
from dream_palace.shared.domain import ApprovalStatus, IncomingMessage, UserContext


class FakeStore:
    def __init__(self, approved: set[int]) -> None:
        self.approved = approved
        self.users: dict[int, dict[str, Any]] = {}
        self.dreams: dict[int, list[dict[str, Any]]] = {}

    def register(self, telegram_id: int, username: str, email: str) -> None:
        self.users[telegram_id] = {"email": email, "status": "pending"}

    def set_approval(self, telegram_id: int, status: ApprovalStatus) -> None:
        self.users.setdefault(telegram_id, {})["status"] = status.value

    def get_user(self, telegram_id: int) -> dict[str, Any] | None:
        return self.users.get(telegram_id)

    def is_approved(self, context: UserContext) -> bool:
        return context.telegram_id in self.approved

    def save_dream(self, context: UserContext, message: IncomingMessage) -> str:
        assert context.telegram_id == message.telegram_id
        self.dreams.setdefault(context.telegram_id, []).append({"text": message.text})
        return "dream-1"

    def list_dreams(
        self,
        context: UserContext,
        since: datetime | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        rows = self.dreams.get(context.telegram_id, [])
        return rows[:limit] if limit else rows


class StubClerk:
    def __init__(self) -> None:
        self.sent: list[tuple[int, str]] = []

    async def send_message(self, chat_id: int, text: str) -> None:
        self.sent.append((chat_id, text))

    async def notify_all(self, chat_ids: frozenset[int], text: str) -> None:
        for chat_id in chat_ids:
            self.sent.append((chat_id, text))


def make_service(approved: set[int]) -> tuple[DreamService, FakeStore, StubClerk]:
    store, clerk = FakeStore(approved), StubClerk()
    return DreamService(store, clerk, frozenset({99})), store, clerk


async def test_unapproved_user_is_rejected() -> None:
    service, _, _ = make_service(set())
    with pytest.raises(PermissionError):
        await service.save_dream(IncomingMessage(telegram_id=42, text="a dream"))
    with pytest.raises(PermissionError):
        service.list_dreams(42)


async def test_dream_is_stored_under_the_active_user() -> None:
    service, store, _ = make_service({42})
    dream_id, text = await service.save_dream(IncomingMessage(telegram_id=42, text="a dream"))
    assert (dream_id, text) == ("dream-1", "a dream")
    assert list(store.dreams) == [42]


async def test_media_dream_is_transcribed_and_stored_as_text() -> None:
    class FakeTranscriber:
        async def transcribe(self, media: bytes, media_type: str) -> str | None:
            assert media_type == "voice"
            return "I was flying over the sea"

    service, store, _ = make_service({42})
    service.transcriber = FakeTranscriber()
    _, text = await service.save_dream(
        IncomingMessage(telegram_id=42, media_type="voice", media_bytes=b"ogg")
    )
    assert text == "I was flying over the sea"
    assert store.dreams[42][0]["text"] == "I was flying over the sea"


async def test_text_dream_skips_transcription() -> None:
    class ExplodingTranscriber:
        async def transcribe(self, media: bytes, media_type: str) -> str | None:
            raise AssertionError("must not be called for text dreams")

    service, _, _ = make_service({42})
    service.transcriber = ExplodingTranscriber()
    _, text = await service.save_dream(IncomingMessage(telegram_id=42, text="just text"))
    assert text == "just text"


def test_retrieval_cannot_cross_user_boundary() -> None:
    service, store, _ = make_service({42})
    store.dreams[7] = [{"text": "another user's dream"}]
    assert service.list_dreams(42) == []


def test_listing_defaults_to_five_dreams() -> None:
    service, store, _ = make_service({42})
    store.dreams[42] = [{"text": f"dream {i}"} for i in range(9)]
    assert len(service.list_dreams(42)) == 5


async def test_analysis_sends_only_the_active_users_dreams() -> None:
    class CapturingAnalyst:
        dreams: list[dict[str, Any]] = []

        async def analyse(self, question: str, dreams: list[dict[str, Any]]) -> str:
            assert question == "What repeats?"
            self.dreams = dreams
            return "Water repeats."

    service, store, _ = make_service({42})
    analyst = CapturingAnalyst()
    service.analyst = analyst
    store.dreams[42] = [{"id": "mine", "text": "blue water"}]
    store.dreams[7] = [{"id": "other", "text": "another user's secret"}]

    assert await service.analyse(42, "What repeats?") == "Water repeats."
    assert analyst.dreams == [{"id": "mine", "text": "blue water"}]


async def test_analysis_falls_back_when_hosted_agent_is_unavailable() -> None:
    class UnavailableAnalyst:
        async def analyse(self, question: str, dreams: list[dict[str, Any]]) -> str:
            raise ConnectionError("Foundry is unavailable")

    service, store, _ = make_service({42})
    service.analyst = UnavailableAnalyst()
    store.dreams[42] = [
        {"text": "blue ocean"},
        {"text": "blue house"},
    ]

    assert await service.analyse(42, "What repeats?") == (
        "2 dreams in the last 30 days. Recurring terms: blue."
    )


async def test_registration_notifies_admins() -> None:
    service, store, clerk = make_service(set())
    await service.register(42, "dima", "dima@example.com")
    assert store.users[42]["status"] == "pending"
    assert clerk.sent and clerk.sent[0][0] == 99


async def test_approval_updates_store_and_notifies_user() -> None:
    service, store, clerk = make_service(set())
    await service.set_approval(42, ApprovalStatus.APPROVED)
    assert store.users[42]["status"] == "approved"
    assert clerk.sent == [(42, "Your Dream Palace registration is approved.")]
