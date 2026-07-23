"""FastAPI app for the Telegram webhook and Mini App."""

from contextlib import asynccontextmanager
from hmac import compare_digest

from azure.identity import DefaultAzureCredential
from fastapi import FastAPI, Header, HTTPException, Request
from telegram import Update

from dream_palace.agents.analysing_agent import AzureFoundryAnalyst
from dream_palace.interface.telegram.bot import build_application
from dream_palace.interface.webapp.api import create_webapp_router
from dream_palace.service.dream_service import DreamService
from dream_palace.service.telegram_client import TelegramClient
from dream_palace.shared.config import Settings
from dream_palace.tools.dream_store import AzureDreamStore


def verify_webhook_secret(expected: str, received: str | None) -> None:
    if not expected or received is None or not compare_digest(received, expected):
        raise HTTPException(status_code=403, detail="invalid Telegram webhook secret")


def create_telegram_app(settings: Settings) -> FastAPI:
    credential = DefaultAzureCredential(managed_identity_client_id=settings.azure_client_id or None)
    store = AzureDreamStore(
        cosmos_endpoint=settings.cosmos_endpoint,
        database_name=settings.cosmos_database_name,
        users_container=settings.cosmos_users_container,
        dreams_container=settings.cosmos_dreams_container,
        storage_account_url=settings.azure_storage_account_url,
        media_container=settings.azure_storage_container,
        credential=credential,
    )
    client = TelegramClient(settings.bot_token)
    analyst = AzureFoundryAnalyst(
        settings.foundry_project_endpoint,
        settings.foundry_agent_name,
        credential,
    )
    service = DreamService(store, client, settings.admins, analyst)
    application = build_application(client, service, settings.admins, settings.webapp_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await application.initialize()
        yield
        await application.shutdown()

    app = FastAPI(title="Dream Palace", lifespan=lifespan)
    app.include_router(create_webapp_router(service, settings.bot_token))

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
