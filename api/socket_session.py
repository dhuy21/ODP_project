"""Read the same signed session cookie the HTTP routes use."""

import json
from base64 import b64decode

import itsdangerous
from itsdangerous.exc import BadSignature

from api.settings import get_settings

SESSION_COOKIE = "session"
SESSION_MAX_AGE = 14 * 24 * 60 * 60


def username_from_cookie_header(cookie_header: str | None) -> str | None:
    """The signed-in username, or None when the cookie is missing or bad."""
    raw = _cookie_value(cookie_header, SESSION_COOKIE)
    if raw is None:
        return None
    signer = itsdangerous.TimestampSigner(get_settings().session_secret)
    try:
        payload = signer.unsign(raw.encode("utf-8"), max_age=SESSION_MAX_AGE)
        data = json.loads(b64decode(payload))
    except (BadSignature, json.JSONDecodeError, ValueError):
        return None
    username = data.get("username") if isinstance(data, dict) else None
    if not isinstance(username, str) or username == "":
        return None
    return username


def _cookie_value(cookie_header: str | None, name: str) -> str | None:
    if not cookie_header:
        return None
    for part in cookie_header.split(";"):
        key, separator, value = part.strip().partition("=")
        if separator and key == name:
            return value
    return None
