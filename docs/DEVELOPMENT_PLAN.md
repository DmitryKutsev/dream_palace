# Dream Palace development plan

## Decisions and invariants

- Telegram is the initial client for registration, approval, dream capture,
  retrieval, and analysis.
- Telegram ID is the tenant key. It comes from the authenticated Telegram
  update or signed Mini App `initData`; it is never accepted from an agent.
- Cosmos DB stores users, approvals, and dream metadata. Blob Storage stores
  media under `users/{telegram_id}/dreams/{dream_id}/...`.
- The Function retrieves a user's journal before calling Microsoft Foundry. The
  hosted agent has no datastore credentials and cannot choose a tenant.
- Azure resources use managed identities. Bot credentials remain in Key Vault,
  outside Terraform state and GitHub secrets.
- The public HTTP edge runs on Azure Functions Flex Consumption. Application
  Insights and Log Analytics provide runtime telemetry.

## Delivery phases

1. Foundation: uv package, domain types, configuration, linting, and pytest.
2. Identity: Telegram registration, approval commands, and approval notices.
3. Ingestion: text and media download, validation, idempotency, and storage.
4. Agents: Foundry hosted analyst, grounded chronological analysis, and
   deterministic fallback.
5. Platform: Flex Consumption, Cosmos DB serverless, Blob Storage, Key Vault,
   managed identities, logging, alerts, and budgets.
6. Migration: dry run, copy, validation, webhook cutover, and rollback window.
7. Hardening: deletion/export, retention, privacy review, load tests, and
   recovery exercises.

## Re-check findings

- Agent prompts are not an authorization boundary. The application filters
  records by authenticated `UserContext` before any model invocation.
- Telegram usernames are mutable and optional; Telegram ID remains the unique
  account key.
- Flex Consumption and Foundry hosted agents have separate scaling and billing
  models. Cold-start and quota behavior must be measured with production-like
  traffic.
- Hosted-agent source deployment is a preview feature, so region and API
  availability must be rechecked before each production rollout.
