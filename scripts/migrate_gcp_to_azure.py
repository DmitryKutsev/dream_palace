"""One-time, resumable Firestore/GCS to Cosmos DB/Blob Storage migration.

The command is read-only unless ``--apply`` is supplied. Both destination writes
are idempotent: Cosmos documents are upserted and existing blobs are skipped.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import firebase_admin
from azure.core.exceptions import ResourceExistsError
from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from firebase_admin import firestore
from google.cloud import storage


@dataclass(frozen=True)
class Config:
    google_project: str
    google_bucket: str
    cosmos_endpoint: str
    cosmos_database: str
    users_container: str
    dreams_container: str
    storage_account_url: str
    media_container: str
    azure_client_id: str | None

    @classmethod
    def from_environment(cls) -> Config:
        return cls(
            google_project=_required("GOOGLE_CLOUD_PROJECT"),
            google_bucket=_required("FIREBASE_STORAGE_BUCKET"),
            cosmos_endpoint=_required("COSMOS_ENDPOINT"),
            cosmos_database=os.getenv("COSMOS_DATABASE_NAME", "dream-palace"),
            users_container=os.getenv("COSMOS_USERS_CONTAINER", "users"),
            dreams_container=os.getenv("COSMOS_DREAMS_CONTAINER", "dreams"),
            storage_account_url=_required("AZURE_STORAGE_ACCOUNT_URL"),
            media_container=os.getenv("AZURE_STORAGE_CONTAINER", "dream-media"),
            azure_client_id=os.getenv("AZURE_CLIENT_ID") or None,
        )


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _json_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def migrate(config: Config, apply: bool) -> tuple[int, int, int]:
    try:
        firebase_admin.get_app()
    except ValueError:
        firebase_admin.initialize_app(options={"projectId": config.google_project})

    source_db = firestore.client()
    source_bucket = storage.Client(project=config.google_project).bucket(config.google_bucket)

    credential = DefaultAzureCredential(managed_identity_client_id=config.azure_client_id)
    database = CosmosClient(config.cosmos_endpoint, credential=credential).get_database_client(
        config.cosmos_database
    )
    users = database.get_container_client(config.users_container)
    dreams = database.get_container_client(config.dreams_container)
    media = BlobServiceClient(
        account_url=config.storage_account_url,
        credential=credential,
    ).get_container_client(config.media_container)

    user_count = dream_count = media_count = 0
    for user_snapshot in source_db.collection("users").stream():
        tenant_id = str(user_snapshot.id)
        user = {
            **_json_value(user_snapshot.to_dict() or {}),
            "id": tenant_id,
            "telegram_id": tenant_id,
        }
        if apply:
            users.upsert_item(user)
        user_count += 1

        for dream_snapshot in user_snapshot.reference.collection("dreams").stream():
            dream = {
                **_json_value(dream_snapshot.to_dict() or {}),
                "id": dream_snapshot.id,
                "user_id": tenant_id,
            }
            if apply:
                dreams.upsert_item(dream)
            dream_count += 1

            media_path = dream.get("media_path")
            if not media_path:
                continue
            if apply:
                payload = source_bucket.blob(str(media_path)).download_as_bytes()
                try:
                    media.upload_blob(name=str(media_path), data=payload, overwrite=False)
                except ResourceExistsError:
                    pass
            media_count += 1

    return user_count, dream_count, media_count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write to Azure. Without this flag the command only counts source records.",
    )
    args = parser.parse_args()
    users, dreams, media = migrate(Config.from_environment(), apply=args.apply)
    mode = "migrated" if args.apply else "found"
    print(f"{mode}: {users} users, {dreams} dreams, {media} media objects")


if __name__ == "__main__":
    main()
