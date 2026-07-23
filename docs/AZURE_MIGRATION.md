# GCP to Azure migration runbook

## Scope

This runbook moves:

- Firestore `users/{telegram_id}` documents to the Cosmos DB `users` container;
- Firestore `users/{telegram_id}/dreams/{dream_id}` documents to the Cosmos DB
  `dreams` container;
- GCS media objects referenced by `media_path` to the private Azure Blob
  `dream-media` container.

It does not delete or mutate GCP resources.

## 1. Prepare and validate Azure

1. Apply `infra/` and seed `bot-token` and `telegram-webhook-secret` in Key
   Vault.
2. Deploy the Function and hosted analyst.
3. Confirm `GET /health` returns `{"status":"ok"}`.
4. Use a development Telegram bot to register, approve, save, list, and analyse
   a test dream.
5. Confirm Cosmos documents use string `telegram_id`/`user_id` partition keys
   and media blobs remain private.

## 2. Dry run

Authenticate to both clouds without exporting credentials:

```bash
gcloud auth application-default login
az login
uv sync --group migration
```

Set the source and destination values:

```bash
export GOOGLE_CLOUD_PROJECT="<gcp-project>"
export FIREBASE_STORAGE_BUCKET="<gcs-bucket>"
export COSMOS_ENDPOINT="<terraform cosmos_endpoint output>"
export COSMOS_DATABASE_NAME="dream-palace"
export COSMOS_USERS_CONTAINER="users"
export COSMOS_DREAMS_CONTAINER="dreams"
export AZURE_STORAGE_ACCOUNT_URL="<terraform storage_account_url output>"
export AZURE_STORAGE_CONTAINER="dream-media"
```

Count the source records without writing:

```bash
uv run --group migration python scripts/migrate_gcp_to_azure.py
```

## 3. Initial copy

```bash
uv run --group migration python scripts/migrate_gcp_to_azure.py --apply
```

The command can be rerun. Documents are upserted by their existing IDs, and a
blob already present at the target path is left unchanged.

## 4. Cut over

1. Announce a short write freeze.
2. Run the migration again with `--apply`.
3. Compare the reported user, dream, and media counts with the dry run.
4. Smoke-test several known users, old dreams, and media objects in Azure.
5. Change the Telegram webhook to the Function URL.
6. Verify `getWebhookInfo`, then test registration, capture, listing, and
   analysis with the production bot.
7. End the write freeze.

Keep Cloud Run, Firestore, and GCS intact but read-only during the rollback
window.

## 5. Roll back

If Azure fails during the rollback window:

1. Pause writes.
2. Point the Telegram webhook back to the former Cloud Run URL.
3. Reconcile dreams created in Azure after cutover before resuming GCP writes.
4. Preserve Azure logs and the failed deployment version for diagnosis.

Do not delete Azure or GCP data during rollback. After the agreed observation
window, export final backups and retire GCP resources through a separately
reviewed change.
