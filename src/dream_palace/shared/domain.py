from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Intent(StrEnum):
    DREAM = "dream"
    RETRIEVE = "retrieve"
    ANALYSE = "analyse"


@dataclass(frozen=True)
class IncomingMessage:
    telegram_id: int
    text: str | None = None
    media_type: str | None = None
    media_bytes: bytes | None = None
    received_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class UserContext:
    telegram_id: int
