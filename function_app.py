"""Azure Functions entry point that adapts the existing FastAPI application."""

import sys
from pathlib import Path

import azure.functions as func

sys.path.insert(0, str(Path(__file__).parent / "src"))

from dream_palace.app import app as fastapi_app  # noqa: E402

app = func.AsgiFunctionApp(
    app=fastapi_app,
    http_auth_level=func.AuthLevel.ANONYMOUS,
)
