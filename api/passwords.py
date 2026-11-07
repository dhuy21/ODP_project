import hashlib


def hash_password(password: str) -> str:
    """Hash a password as a SHA-256 hex digest of its UTF-8 bytes."""
    return hashlib.sha256(password.encode()).hexdigest()
