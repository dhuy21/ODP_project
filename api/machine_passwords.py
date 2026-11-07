import base64
import hashlib

from cryptography.fernet import Fernet

from api.settings import get_settings


def fernet_key() -> bytes:
    """Derive a Fernet key from the configured ENCRYPTION_KEY or its default."""
    settings = get_settings()
    if settings.encryption_key:
        return settings.encryption_key.encode()
    material = hashlib.sha256(settings.fernet_secret.encode()).digest()
    return base64.urlsafe_b64encode(material)


def encrypt_machine_password(plaintext: str) -> str:
    token = Fernet(fernet_key()).encrypt(plaintext.encode())
    return token.decode("utf-8")


def decrypt_machine_password(token: str) -> str:
    """Plain machine password. Caller must not send this to the browser."""
    return Fernet(fernet_key()).decrypt(token.encode()).decode("utf-8")
