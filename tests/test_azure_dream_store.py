from datetime import UTC, datetime
from typing import Any

import pytest

from dream_palace.shared.domain import IncomingMessage, UserContext
from dream_palace.tools.dream_store import AzureDreamStore


class FakeDreamsContainer:
    def __init__(self) -> None:
        self.created: list[dict[str, Any]] = []
        self.queries: list[dict[str, Any]] = []

    def create_item(self, body: dict[str, Any]) -> None:
        self.created.append(body)

    def query_items(self, **kwargs: Any) -> list[dict[str, Any]]:
        self.queries.append(kwargs)
        return [{"id": "mine", "user_id": kwargs["partition_key"]}]


class FakeMediaContainer:
    def __init__(self) -> None:
        self.uploads: list[dict[str, Any]] = []

    def upload_blob(self, **kwargs: Any) -> None:
        self.uploads.append(kwargs)


def make_store() -> tuple[AzureDreamStore, FakeDreamsContainer, FakeMediaContainer]:
    store = AzureDreamStore.__new__(AzureDreamStore)
    dreams = FakeDreamsContainer()
    media = FakeMediaContainer()
    store._dreams = dreams
    store._media = media
    return store, dreams, media


def test_save_rejects_a_message_from_another_tenant() -> None:
    store, dreams, media = make_store()

    with pytest.raises(PermissionError):
        store.save_dream(
            UserContext(telegram_id=42),
            IncomingMessage(telegram_id=7, text="not mine"),
        )

    assert dreams.created == []
    assert media.uploads == []


def test_media_is_namespaced_and_document_is_partitioned_by_user() -> None:
    store, dreams, media = make_store()
    received_at = datetime(2026, 7, 23, 8, 30, tzinfo=UTC)

    dream_id = store.save_dream(
        UserContext(telegram_id=42),
        IncomingMessage(
            telegram_id=42,
            text="ocean",
            media_type="voice",
            media_bytes=b"ogg",
            received_at=received_at,
        ),
    )

    assert media.uploads == [
        {
            "name": f"users/42/dreams/{dream_id}/voice",
            "data": b"ogg",
            "overwrite": False,
        }
    ]
    assert dreams.created[0]["id"] == dream_id
    assert dreams.created[0]["user_id"] == "42"
    assert dreams.created[0]["received_at"] == received_at.isoformat()


def test_list_dreams_uses_the_active_tenant_as_the_cosmos_partition() -> None:
    store, dreams, _ = make_store()

    rows = store.list_dreams(UserContext(telegram_id=42), limit=5)

    assert rows == [{"id": "mine", "user_id": "42"}]
    assert dreams.queries[0]["partition_key"] == "42"
    assert {"name": "@user_id", "value": "42"} in dreams.queries[0]["parameters"]
