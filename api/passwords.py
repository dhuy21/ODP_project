import hashlib


def hash_password(password: str) -> str:
    """Same digest Flask stores: SHA-256 hex of the UTF-8 password."""
    return hashlib.sha256(password.encode()).hexdigest()
