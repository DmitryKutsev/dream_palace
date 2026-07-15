# Dream Palace

Telegram-first private dream journal using Google ADK, Firebase/Firestore, and GCS.

## Structure

- `src/dream_palace/bots`: Clerk registration and Dreamer ingestion bots
- `src/dream_palace/agents.py`: conservative routing and tenant-safe tools
- `src/dream_palace/adk_app.py`: Google ADK agent definition
- `src/dream_palace/storage.py`: Firestore metadata and GCS media adapter
- `infra`: Terraform for Google APIs, storage, and workload identity
- `.github/workflows`: UV/pytest CI and keyless deployment scaffold
- `docs/DEVELOPMENT_PLAN.md`: reviewed delivery plan and security decisions

## Development

```bash
cp .env.example .env
make install
make test
make lint
```

Run the bots independently with `make run-clerk` and `make run-dreamer`.
This is a secure skeleton, not a production deployment.
