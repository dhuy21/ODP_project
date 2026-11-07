from api.errors import FieldTooLong, UsernameReserved
from api.passwords import hash_password
from api.user_sql import ensure_default_admin, insert_user
from api.usernames import RESERVED_USERNAMES


def register_user(username: str, email: str, password: str) -> None:
    """Create a user account. Role is always user. Admin is seeded separately."""
    ensure_default_admin()
    if username.lower() in RESERVED_USERNAMES:
        raise UsernameReserved(username)
    if len(username) > 32 or len(email) > 100:
        raise FieldTooLong()
    insert_user(username, email, hash_password(password))
