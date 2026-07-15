from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import uuid4

import firebase_admin
from firebase_admin import firestore
from google.cloud import storage

from dream_palace.domain import ApprovalStatus, IncomingMessage, UserContext


class DreamStore(Protocol):
    def is_approved(self, context: UserContext) -> bool: ...
    def save_dream(self, context: UserContext, message: IncomingMessage) -> str: ...
    def list_dreams(self, context: UserContext) -> list[dict[str, Any]]: ...


class FirebaseDreamStore:
    """Tenant-scoped storage; public methods derive paths only from active user context."""

    def __init__(self, project_id: str, bucket_name: str) -> None:
        try:
            firebase_admin.get_app()
        except ValueError:
            firebase_admin.initialize_app(options={"projectId": project_id})
        self._db = firestore.client()
        self._bucket = storage.Client(project=project_id).bucket(bucket_name)

    def register(self, telegram_id: int, username: str, email: str) -> None:
        self._db.collection("users").document(str(telegram_id)).set(
            {
                "telegram_id": telegram_id,
                "username": username,
                "email": email,
                "status": ApprovalStatus.PENDING.value,
                "created_at": datetime.now(UTC),
            },
            merge=True,
        )

    def set_approval(self, telegram_id: int, status: ApprovalStatus) -> None:
        self._db.collection("users").document(str(telegram_id)).update({"status": status.value})

    def is_approved(self, context: UserContext) -> bool:
        snapshot = self._db.collection("users").document(str(context.telegram_id)).get()
        return snapshot.exists and snapshot.to_dict().get("status") == ApprovalStatus.APPROVED.value

    def save_dream(self, context: UserContext, message: IncomingMessage) -> str:
        if message.telegram_id != context.telegram_id:
            raise PermissionError("message tenant does not match active Telegram user")
        dream_id = uuid4().hex
        media_path = None
        if message.media_bytes is not None:
            media_path = f"users/{context.telegram_id}/dreams/{dream_id}/{message.media_type}"
            self._bucket.blob(media_path).upload_from_string(message.media_bytes)
        self._db.collection("users").document(str(context.telegram_id)).collection(
            "dreams"
        ).document(dream_id).set(
            {
                "text": message.text,
                "media_type": message.media_type,
                "media_path": media_path,
                "received_at": message.received_at,
            }
        )
        return dream_id

    def list_dreams(self, context: UserContext) -> list[dict[str, Any]]:
        query = (
            self._db.collection("users")
            .document(str(context.telegram_id))
            .collection("dreams")
            .order_by("received_at")
        )
        return [{"id": row.id, **row.to_dict()} for row in query.stream()]
