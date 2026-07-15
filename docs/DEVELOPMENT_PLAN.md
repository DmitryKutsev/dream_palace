# Dream Palace development plan

## Decisions and invariants

- Telegram is the initial client: Clerk handles registration/approval; Dreamer handles text, voice, and images.
- Telegram ID is the tenant key. It comes from the authenticated Telegram update and is never accepted from an agent/model argument.
- Firestore stores users, approvals, and dream metadata. A Firebase-managed GCS bucket stores binary media under `users/{telegram_id}/...`.
- The orchestrator routes only explicit retrieval and analysis requests; every uncertain input is stored as a dream.
- Analysis returns dreams chronologically and highlights significant people, names, and recurring characters.
- Google ADK agents run on managed Google infrastructure. Terraform manages cloud resources; GitHub Actions uses keyless Workload Identity Federation.

## Delivery phases

1. Foundation: UV package, domain types, configuration, Make targets, linting, and pytest.
2. Identity: Clerk registration conversation, admin approval commands, audit trail, and approval notifications.
3. Ingestion: text/image/voice downloads, validation, transcription, image understanding, idempotency, and storage.
4. Agents: ADK classifier/orchestrator, retrieval tools, chronological analysis, entity extraction, and recurrence scoring.
5. Platform: Firebase bootstrap, GCS lifecycle, Secret Manager, hosted runtime, logging, alerts, and budgets.
6. Hardening: Firestore rules, emulator integration tests, prompt-injection tests, deletion/export, retention, and privacy review.
7. Release: staging, end-to-end Telegram tests, admin runbook, disaster recovery, and controlled rollout.

## Re-check findings

- “Firebase free tier GCS storage” spans two services: Firestore fits structured records; the Firebase/GCS bucket fits voice/image objects. Verify free-tier limits for the deployment region.
- Telegram usernames are mutable and optional. Telegram ID is the unique identity; email and username are profile fields.
- Agent prompts cannot enforce isolation. Python constructs storage paths from `UserContext.telegram_id`, with cross-user tests.
- Classification false positives could expose data. Only explicit retrieve/analyse prefixes leave the safe dream-storage default.
- Cloud Run deployment and authenticated Telegram webhook handling are scaffolded. Agent Engine deployment still requires the GCP project, target, bot secrets, and environment policy.
