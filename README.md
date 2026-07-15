# Dream Palace

Telegram-first private dream journal using Google ADK, Firebase/Firestore, and GCS.

## Structure

- `src/dream_palace/app.py`: application composition root and ASGI entrypoint
- `src/dream_palace/agents`: Google ADK agent, prompts, and conservative orchestration
- `src/dream_palace/tools`: tenant-safe Firestore and GCS tools
- `src/dream_palace/interface/telegram`: Clerk, Dreamer, and webhook interface
- `src/dream_palace/shared`: configuration and domain types
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

Run the webhook service locally with `make run`. This is a secure skeleton, not a production
deployment.

## Telegram webhook setup

Deploy the ASGI app (`dream_palace.app:app`) to an HTTPS endpoint, for example Cloud Run,
and set `WEBHOOK_BASE_URL` and a long random `WEBHOOK_SECRET`. Register each bot webhook:

```bash
export WEBHOOK_BASE_URL="https://dream-palace-xxxxx-ew.a.run.app"
export WEBHOOK_SECRET="$(openssl rand -hex 32)"

curl -fsS "https://api.telegram.org/bot${CLERK_BOT_TOKEN}/setWebhook" \
  -d "url=${WEBHOOK_BASE_URL}/webhooks/clerk" \
  -d "secret_token=${WEBHOOK_SECRET}" \
  -d 'allowed_updates=["message"]'

curl -fsS "https://api.telegram.org/bot${DREAMER_BOT_TOKEN}/setWebhook" \
  -d "url=${WEBHOOK_BASE_URL}/webhooks/dreamer" \
  -d "secret_token=${WEBHOOK_SECRET}" \
  -d 'allowed_updates=["message"]'
```

Telegram sends the secret as `X-Telegram-Bot-Api-Secret-Token`; the app rejects missing or
incorrect values. Confirm registration without printing tokens:

```bash
curl -fsS "https://api.telegram.org/bot${CLERK_BOT_TOKEN}/getWebhookInfo"
curl -fsS "https://api.telegram.org/bot${DREAMER_BOT_TOKEN}/getWebhookInfo"
```

The application is webhook-only; it does not start Telegram long polling.
