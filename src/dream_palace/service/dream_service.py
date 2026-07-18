"""Backend service: registration, approval, dream retrieval, and analysis."""

from __future__ import annotations

from collections import Counter
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from dream_palace.agents.analysing_agent import run_analysis
from dream_palace.service.telegram_client import TelegramClient
from dream_palace.shared.domain import ApprovalStatus, IncomingMessage, UserContext


class UserDreamStore(Protocol):
    """Dream storage plus the user directory it currently hosts."""

    def register(self, telegram_id: int, username: str, email: str) -> None: ...
    def set_approval(self, telegram_id: int, status: ApprovalStatus) -> None: ...
    def get_user(self, telegram_id: int) -> dict[str, Any] | None: ...
    def is_approved(self, context: UserContext) -> bool: ...
    def save_dream(self, context: UserContext, message: IncomingMessage) -> str: ...
    def list_dreams(
        self,
        context: UserContext,
        since: datetime | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]: ...


class Transcriber(Protocol):
    async def transcribe(self, media: bytes, media_type: str) -> str | None: ...


class DreamService:
    """Every operation is bound to the Telegram id of the authenticated caller."""

    DEFAULT_LIMIT = 5

    def __init__(
        self,
        store: UserDreamStore,
        clerk: TelegramClient,
        admins: frozenset[int],
        model: str,
        transcriber: Transcriber | None = None,
    ) -> None:
        self.store = store
        self.clerk = clerk
        self.admins = admins
        self.model = model
        self.transcriber = transcriber

    async def register(self, telegram_id: int, username: str, email: str) -> None:
        self.store.register(telegram_id, username, email)
        await self.clerk.notify_all(
            self.admins,
            f"Registration from @{username or '-'} ({telegram_id}, {email}). "
            f"Approve with /approve {telegram_id} or reject with /reject {telegram_id}.",
        )

    async def set_approval(self, telegram_id: int, status: ApprovalStatus) -> None:
        self.store.set_approval(telegram_id, status)
        await self.clerk.send_message(
            telegram_id, f"Your Dream Palace registration is {status.value}."
        )

    def user_status(self, telegram_id: int) -> str | None:
        user = self.store.get_user(telegram_id)
        return user.get("status") if user else None

    def is_approved(self, telegram_id: int) -> bool:
        return self.store.is_approved(UserContext(telegram_id=telegram_id))

    async def save_dream(self, message: IncomingMessage) -> tuple[str, str | None]:
        """Store the dream (transcribing media to text first) and return (id, text)."""
        context = UserContext(telegram_id=message.telegram_id)
        if not self.store.is_approved(context):
            raise PermissionError("user is not approved")
        text = message.text
        if message.media_bytes is not None and self.transcriber is not None:
            transcript = await self.transcriber.transcribe(
                message.media_bytes, message.media_type or ""
            )
            if transcript:
                text = f"{text}\n\n{transcript}" if text else transcript
        if text != message.text:
            message = replace(message, text=text)
        return self.store.save_dream(context, message), text

    def list_dreams(
        self, telegram_id: int, days: int | None = None, limit: int | None = DEFAULT_LIMIT
    ) -> list[dict[str, Any]]:
        context = UserContext(telegram_id=telegram_id)
        if not self.store.is_approved(context):
            raise PermissionError("user is not approved")
        since = datetime.now(UTC) - timedelta(days=days) if days else None
        return self.store.list_dreams(context, since=since, limit=limit)

    async def analyse(self, telegram_id: int, question: str, days: int = 30) -> str:
        context = UserContext(telegram_id=telegram_id)
        if not self.store.is_approved(context):
            raise PermissionError("user is not approved")
        try:
            analysis = await run_analysis(self.model, self.store, context, question)
            if analysis.strip():
                return analysis
        except Exception:  # model unavailable — fall back to a deterministic summary
            pass
        return self._fallback_summary(context, days)

    def _fallback_summary(self, context: UserContext, days: int) -> str:
        since = datetime.now(UTC) - timedelta(days=days)
        dreams = self.store.list_dreams(context, since=since)
        if not dreams:
            return f"No dreams recorded in the last {days} days."
        words = [
            word.strip('.,!?"').lower()
            for dream in dreams
            for word in (dream.get("text") or "").split()
        ]
        repeated = [
            word for word, count in Counter(words).most_common() if count > 1 and len(word) > 2
        ]
        themes = ", ".join(repeated[:10]) or "none detected"
        return f"{len(dreams)} dreams in the last {days} days. Recurring terms: {themes}."
