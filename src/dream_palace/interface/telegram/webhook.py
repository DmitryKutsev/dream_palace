"""FastAPI app: Telegram webhook and the mini app."""

import os
from contextlib import asynccontextmanager
from hmac import compare_digest

from fastapi import FastAPI, Header, HTTPException, Request
from telegram import Update

from dream_palace.interface.telegram.bot import build_application
from dream_palace.interface.webapp.api import create_webapp_router
from dream_palace.service.dream_service import DreamService
from dream_palace.service.telegram_client import TelegramClient
from dream_palace.service.transcription import GeminiTranscriber
from dream_palace.shared.config import Settings
from dream_palace.tools.dream_store import FirebaseDreamStore


def verify_webhook_secret(expected: str, received: str | None) -> None:
    if not expected or received is None or not compare_digest(received, expected):
        raise HTTPException(status_code=403, detail="invalid Telegram webhook secret")


def create_telegram_app(settings: Settings) -> FastAPI:
    store = FirebaseDreamStore(settings.google_cloud_project, settings.firebase_storage_bucket)
    client = TelegramClient(settings.bot_token)
    transcriber = None
    if settings.google_api_key:
        # Also export for the ADK analysing agent, which reads the env directly.
        os.environ.setdefault("GOOGLE_API_KEY", settings.google_api_key)
        transcriber = GeminiTranscriber(settings.google_api_key, settings.adk_model)
    service = DreamService(store, client, settings.admins, settings.adk_model, transcriber)
    application = build_application(client, service, settings.admins, settings.webapp_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await application.initialize()
        yield
        await application.shutdown()

    app = FastAPI(title="Dream Palace", lifespan=lifespan)
    app.include_router(create_webapp_router(service, settings.bot_token))

    # /healthz is intercepted by Google's frontend on run.app domains; use /health.
    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/webhooks/telegram")
    async def telegram_webhook(
        request: Request, x_telegram_bot_api_secret_token: str | None = Header(default=None)
    ) -> dict[str, bool]:
        verify_webhook_secret(settings.webhook_secret, x_telegram_bot_api_secret_token)
        await application.process_update(Update.de_json(await request.json(), application.bot))
        return {"ok": True}

    return app
