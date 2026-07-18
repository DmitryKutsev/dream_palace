"""Abstract database adapter for user accounts (register / sign in / access).

Concrete infrastructure (SQLite for local, or a hosted Postgres such as Neon)
is deliberately deferred; implementations subclass ``DatabaseAdapter``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from pydantic import BaseModel


class DatabaseConfig(BaseModel):
    connection_string: str
    echo: bool = False


class UserRecord(BaseModel):
    telegram_id: int
    username: str = ""
    email: str = ""
    registered: bool = False
    access_level: str = "pending"  # pending | approved | rejected | admin
    created_at: datetime | None = None


class DreamEntry(BaseModel):
    user_id: int
    content: str
    title: str | None = None
    tags: list[str] = []
    id: str | None = None
    created_at: datetime | None = None


class DatabaseAdapter(ABC):
    """User-account storage boundary. Every query is keyed by ``telegram_id``."""

    def __init__(self, config: DatabaseConfig) -> None:
        self.config = config

    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...

    @abstractmethod
    async def create_user(self, user: UserRecord) -> UserRecord: ...

    @abstractmethod
    async def get_user(self, telegram_id: int) -> UserRecord | None: ...

    @abstractmethod
    async def set_access_level(self, telegram_id: int, access_level: str) -> None: ...
