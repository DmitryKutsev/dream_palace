import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest

from dream_palace.interface.webapp.auth import InitDataError, validate_init_data

BOT_TOKEN = "12345:TEST_TOKEN"


def sign(params: dict[str, str], token: str = BOT_TOKEN) -> str:
    check_string = "\n".join(f"{key}={value}" for key, value in sorted(params.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    params = {**params, "hash": hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()}
    return urlencode(params)


def make_init_data(user_id: int = 42, auth_date: int | None = None) -> str:
    return sign(
        {
            "auth_date": str(auth_date or int(time.time())),
            "query_id": "AAF",
            "user": json.dumps({"id": user_id, "first_name": "Dima", "username": "dima"}),
        }
    )


def test_valid_init_data_returns_user() -> None:
    user = validate_init_data(make_init_data(user_id=42), BOT_TOKEN)
    assert user["id"] == 42


def test_tampered_user_is_rejected() -> None:
    init_data = make_init_data(user_id=42).replace("42", "43")
    with pytest.raises(InitDataError):
        validate_init_data(init_data, BOT_TOKEN)


def test_wrong_bot_token_is_rejected() -> None:
    with pytest.raises(InitDataError):
        validate_init_data(make_init_data(), "999:OTHER_TOKEN")


def test_expired_init_data_is_rejected() -> None:
    stale = make_init_data(auth_date=int(time.time()) - 100_000)
    with pytest.raises(InitDataError):
        validate_init_data(stale, BOT_TOKEN)


def test_missing_hash_is_rejected() -> None:
    with pytest.raises(InitDataError):
        validate_init_data("auth_date=1&user=%7B%22id%22%3A1%7D", BOT_TOKEN)
