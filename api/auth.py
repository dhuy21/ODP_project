import hmac

from fastapi import Request

from api.passwords import hash_password
from api.responses import ADMIN_REQUIRED, AUTH_REQUIRED, error_response
from api.user_sql import find_user_credentials, find_user_role


def authenticate(username: str, password: str):
    """Return username and role, or None. Unknown user and bad password look the same."""
    candidate = hash_password(password)
    row = find_user_credentials(username)
    stored = row["password_hash"] if row is not None else ""
    if row is None or not isinstance(stored, str) or not hmac.compare_digest(stored, candidate):
        return None
    return {"username": row["username"], "role": row["role"]}


def admin_denial(request: Request):
    """An error response when the caller is not an admin. None when they are.

    The database role decides. A stale role in the cookie is not enough.
    """
    username = request.session.get("username")
    if not username:
        return error_response(AUTH_REQUIRED, 401)
    role = find_user_role(username)
    if role is None:
        request.session.clear()
        return error_response(AUTH_REQUIRED, 401)
    if role != "admin":
        return error_response(ADMIN_REQUIRED, 403)
    return None
