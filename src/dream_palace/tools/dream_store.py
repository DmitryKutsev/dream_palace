from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import uuid4

from azure.core.credentials import TokenCredential
from azure.cosmos import ContainerProxy, CosmosClient
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from azure.storage.blob import BlobServiceClient

from dream_palace.shared.domain import ApprovalStatus, IncomingMessage, UserContext


class DreamStore(Protocol):
    def is_approved(self, context: UserContext) -> bool: ...
    def save_dream(self, context: UserContext, message: IncomingMessage) -> str: ...
    def list_dreams(
        self,
        context: UserContext,
        since: datetime | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]: ...


class AzureDreamStore:
    """Cosmos DB/Blob store with all operations bound to an authenticated tenant."""

    def __init__(
        self,
        cosmos_endpoint: str,
        database_name: str,
        users_container: str,
        dreams_container: str,
        storage_account_url: str,
        media_container: str,
        credential: TokenCredential,
    ) -> None:
        database = CosmosClient(cosmos_endpoint, credential=credential).get_database_client(
            database_name
        )
        self._users: ContainerProxy = database.get_container_client(users_container)
        self._dreams: ContainerProxy = database.get_container_client(dreams_container)
        self._media = BlobServiceClient(
            account_url=storage_account_url, credential=credential
        ).get_container_client(media_container)

    def register(self, telegram_id: int, username: str, email: str) -> None:
        tenant_id = str(telegram_id)
        existing = self.get_user(telegram_id) or {}
        self._users.upsert_item(
            {
                **existing,
                "id": tenant_id,
                "telegram_id": tenant_id,
                "username": username,
                "email": email,
                "status": existing.get("status", ApprovalStatus.PENDING.value),
                "created_at": existing.get("created_at", datetime.now(UTC).isoformat()),
            }
        )

    def set_approval(self, telegram_id: int, status: ApprovalStatus) -> None:
        tenant_id = str(telegram_id)
        user = self._users.read_item(item=tenant_id, partition_key=tenant_id)
        user["status"] = status.value
        self._users.replace_item(item=tenant_id, body=user)

    def is_approved(self, context: UserContext) -> bool:
        user = self.get_user(context.telegram_id)
        return bool(user and user.get("status") == ApprovalStatus.APPROVED.value)

    def save_dream(self, context: UserContext, message: IncomingMessage) -> str:
        if message.telegram_id != context.telegram_id:
            raise PermissionError("message tenant does not match active Telegram user")
        dream_id = uuid4().hex
        tenant_id = str(context.telegram_id)
        media_path = None
        if message.media_bytes is not None:
            media_path = f"users/{tenant_id}/dreams/{dream_id}/{message.media_type or 'media'}"
            self._media.upload_blob(
                name=media_path,
                data=message.media_bytes,
                overwrite=False,
            )
        self._dreams.create_item(
            {
                "id": dream_id,
                "user_id": tenant_id,
                "text": message.text,
                "media_type": message.media_type,
                "media_path": media_path,
                "received_at": message.received_at.astimezone(UTC).isoformat(),
            }
        )
        return dream_id

    def get_user(self, telegram_id: int) -> dict[str, Any] | None:
        tenant_id = str(telegram_id)
        try:
            return self._users.read_item(item=tenant_id, partition_key=tenant_id)
        except CosmosResourceNotFoundError:
            return None

    def list_dreams(
        self,
        context: UserContext,
        since: datetime | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        tenant_id = str(context.telegram_id)
        query = "SELECT * FROM dreams d WHERE d.user_id = @user_id"
        parameters: list[dict[str, Any]] = [{"name": "@user_id", "value": tenant_id}]
        if since is not None:
            query += " AND d.received_at >= @since"
            parameters.append({"name": "@since", "value": since.astimezone(UTC).isoformat()})
        query += " ORDER BY d.received_at DESC"
        if limit is not None:
            query += " OFFSET 0 LIMIT @limit"
            parameters.append({"name": "@limit", "value": limit})
        return list(
            self._dreams.query_items(
                query=query,
                parameters=parameters,
                partition_key=tenant_id,
            )
        )
