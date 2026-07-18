# Dream Palace

Telegram-first private dream journal: python-telegram-bot + FastAPI on Cloud Run,
Firestore/GCS for storage, Google ADK (Gemini) for dream analysis, and a Telegram
Mini App for browsing and analysing your dreams.

## Structure

- `src/dream_palace/app.py`: application composition root and ASGI entrypoint
- `src/dream_palace/service`: backend services (`DreamService`, `TelegramClient`)
- `src/dream_palace/agents`: ADK agents and prompts; the analysing agent's dream tool
  is bound to the authenticated user in Python, never chosen by the model
- `src/dream_palace/tools`: tenant-safe Firestore and GCS dream store
- `src/dream_palace/interface/telegram`: bot handlers (registration, approval, dream intake) and the webhook route
- `src/dream_palace/interface/webapp`: Telegram Mini App (initData auth, dreams API)
- `src/dream_palace/adapters`: abstract database/LLM adapters (concrete infra deferred)
- `src/dream_palace/shared`: configuration and domain types
- `infra`: Terraform for Google APIs, storage, and workload identity
- `docs/DEVELOPMENT_PLAN.md`: reviewed delivery plan and security decisions

## Development

```bash
cp .env.example .env
make install
make test
make lint
make run   # uvicorn on :8080
```

## Manual setup

Telegram allows exactly one webhook URL per bot, so a bot cannot serve local and
production at once. Create **one bot per environment**: a `_dev` bot for local work
and a production bot.

### 1. One-time Google setup

- In the Firebase console: create (or reuse) the project, enable **Firestore in
  Native mode** and the **Storage bucket**.
- Locally: `gcloud auth application-default login` so `firebase_admin`/GCS can
  authenticate (or point `GOOGLE_APPLICATION_CREDENTIALS` at a service-account file).
- Get a **Gemini API key** from [aistudio.google.com](https://aistudio.google.com)
  for the analysing agent (`GOOGLE_API_KEY`).

### 2. BotFather

- `/newbot` twice (one dev bot, one prod bot); save the tokens.
- No extra BotFather configuration is needed for the mini app button — it only
  requires `WEBAPP_URL` to be HTTPS.
- Get your own Telegram id from @userinfobot and put it in `ADMIN_TELEGRAM_IDS`.

### 3. Local run

```bash
cp .env.example .env                 # dev tokens; WEBHOOK_SECRET=$(openssl rand -hex 32)
uv run uvicorn dream_palace.app:app --port 8080
cloudflared tunnel --url http://localhost:8080   # or: ngrok http 8080
```

Put the tunnel URL into `.env` as `WEBAPP_URL=https://<tunnel-host>/app`, restart
uvicorn, then register the webhook (repeat when the tunnel URL changes):

```bash
curl -fsS "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -d "url=https://<tunnel-host>/webhooks/telegram" \
  -d "secret_token=${WEBHOOK_SECRET}" \
  -d 'allowed_updates=["message"]'
```

Verify with `getWebhookInfo` (prints no tokens):

```bash
curl -fsS "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo"
```

Test the loop: `/start` the bot → button opens the mini app → register →
`/approve <your-id>` from the admin account → send a dream to the bot →
see it under "Your dreams" → analyse.

### 4. Cloud Run

```bash
gcloud run deploy dream-palace --source . --region europe-west1 --allow-unauthenticated \
  --set-env-vars BOT_TOKEN=...,ADMIN_TELEGRAM_IDS=...,GOOGLE_CLOUD_PROJECT=...,FIREBASE_STORAGE_BUCKET=...,WEBHOOK_SECRET=...,GOOGLE_API_KEY=...
```

- Grant the service's runtime service account `roles/datastore.user` and storage
  access on the bucket.
- The service URL is only known after the first deploy; then set
  `gcloud run services update dream-palace --set-env-vars WEBAPP_URL=https://<run-url>/app`
  and run the two `setWebhook` calls above with the **prod** tokens and the run URL.
- `--allow-unauthenticated` is required (Telegram must reach the webhook); access is
  gated by the webhook secret and the mini app's initData HMAC instead.
- Recommended once the flow works: move tokens from `--set-env-vars` to Secret
  Manager (`--set-secrets`).

Telegram sends the secret as `X-Telegram-Bot-Api-Secret-Token`; the app rejects
missing or incorrect values. The application is webhook-only; it does not start
Telegram long polling.
