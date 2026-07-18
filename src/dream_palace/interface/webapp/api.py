"""Mini App backend: serves the page and a small API authenticated via initData.

No ``from __future__ import annotations`` here: stringized annotations would
stop FastAPI from resolving ``Depends(current_user)`` on the closure-scoped
dependency, silently turning it into a query parameter.
"""

from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from dream_palace.interface.webapp.auth import InitDataError, validate_init_data
from dream_palace.service.dream_service import DreamService

STATIC_DIR = Path(__file__).parent / "static"


class RegisterPayload(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AnalysePayload(BaseModel):
    question: str = "Analyse my recent dreams for recurring themes."
    days: int = 30


def create_webapp_router(service: DreamService, bot_token: str) -> APIRouter:
    router = APIRouter()

    def current_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
        scheme, _, init_data = (authorization or "").partition(" ")
        if scheme != "tma" or not init_data:
            raise HTTPException(status_code=401, detail="expected 'Authorization: tma <initData>'")
        try:
            return validate_init_data(init_data, bot_token)
        except InitDataError as error:
            raise HTTPException(status_code=401, detail=str(error)) from error

    @router.get("/app", response_class=HTMLResponse)
    async def index() -> str:
        return (STATIC_DIR / "index.html").read_text()

    @router.get("/api/me")
    async def me(user: Annotated[dict[str, Any], Depends(current_user)]) -> dict[str, Any]:
        status = service.user_status(int(user["id"]))
        return {"registered": status is not None, "status": status}

    @router.post("/api/register")
    async def register(
        payload: RegisterPayload, user: Annotated[dict[str, Any], Depends(current_user)]
    ) -> dict[str, str]:
        await service.register(int(user["id"]), user.get("username") or "", payload.email)
        return {"status": "pending"}

    @router.get("/api/dreams")
    async def dreams(
        user: Annotated[dict[str, Any], Depends(current_user)],
        days: int | None = None,
        limit: int = DreamService.DEFAULT_LIMIT,
    ) -> dict[str, Any]:
        try:
            rows = service.list_dreams(int(user["id"]), days=days, limit=min(limit, 100))
        except PermissionError as error:
            raise HTTPException(status_code=403, detail="registration not approved") from error
        return {
            "dreams": [
                {
                    "id": row.get("id"),
                    "text": row.get("text"),
                    "media_type": row.get("media_type"),
                    "received_at": str(row.get("received_at")),
                }
                for row in rows
            ]
        }

    @router.post("/api/analyse")
    async def analyse(
        payload: AnalysePayload, user: Annotated[dict[str, Any], Depends(current_user)]
    ) -> dict[str, str]:
        try:
            analysis = await service.analyse(int(user["id"]), payload.question, payload.days)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail="registration not approved") from error
        return {"analysis": analysis}

    return router
