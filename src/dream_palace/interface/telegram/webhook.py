from hmac import compare_digest

from aiogram import Bot
from aiogram.types import Update
from fastapi import FastAPI, Header, HTTPException, Request

from dream_palace.interface.telegram.clerk import build_dispatcher as build_clerk
from dream_palace.interface.telegram.dreamer import build_dispatcher as build_dreamer
from dream_palace.shared.config import Settings
from dream_palace.tools import FirebaseDreamStore


def verify_webhook_secret(expected: str, received: str | None) -> None:
    if not expected or received is None or not compare_digest(received, expected):
        raise HTTPException(status_code=403, detail="invalid Telegram webhook secret")


def create_telegram_app(settings: Settings) -> FastAPI:
    clerk_bot = Bot(settings.clerk_bot_token)
    dreamer_bot = Bot(settings.dreamer_bot_token)
    store = FirebaseDreamStore(settings.google_cloud_project, settings.firebase_storage_bucket)
    clerk = build_clerk(clerk_bot, store, settings.admins)
    dreamer = build_dreamer(dreamer_bot, store)
    app = FastAPI(title="Dream Palace Telegram interface")

    @app.get("/healthz")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/webhooks/clerk")
    async def clerk_webhook(
        request: Request, x_telegram_bot_api_secret_token: str | None = Header(default=None)
    ) -> dict[str, bool]:
        verify_webhook_secret(settings.webhook_secret, x_telegram_bot_api_secret_token)
        await clerk.feed_update(clerk_bot, Update.model_validate(await request.json()))
        return {"ok": True}

    @app.post("/webhooks/dreamer")
    async def dreamer_webhook(
        request: Request, x_telegram_bot_api_secret_token: str | None = Header(default=None)
    ) -> dict[str, bool]:
        verify_webhook_secret(settings.webhook_secret, x_telegram_bot_api_secret_token)
        await dreamer.feed_update(dreamer_bot, Update.model_validate(await request.json()))
        return {"ok": True}

    return app
