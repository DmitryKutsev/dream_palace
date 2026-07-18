"""Telegram Mini App initData validation (HMAC, per Telegram WebApp spec)."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any
from urllib.parse import parse_qsl


class InitDataError(ValueError):
    """The initData payload is missing, stale, or fails HMAC verification."""


def validate_init_data(
    init_data: str, bot_token: str, max_age_seconds: int = 86400
) -> dict[str, Any]:
    """Verify initData signed by Telegram and return the authenticated user object.

    The returned user's ``id`` is the only source of the tenant identity used by
    the API — the client can never claim someone else's id without breaking the
    HMAC.
    """
    try:
        pairs = dict(parse_qsl(init_data, strict_parsing=True))
    except ValueError as error:
        raise InitDataError("malformed initData") from error
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise InitDataError("initData has no hash")
    check_string = "\n".join(f"{key}={value}" for key, value in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received_hash):
        raise InitDataError("initData hash mismatch")
    auth_date = int(pairs.get("auth_date", "0"))
    if max_age_seconds and time.time() - auth_date > max_age_seconds:
        raise InitDataError("initData is expired")
    user = json.loads(pairs.get("user", "{}"))
    if not isinstance(user, dict) or "id" not in user:
        raise InitDataError("initData has no user")
    return user
