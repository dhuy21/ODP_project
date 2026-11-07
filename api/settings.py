import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ENV_PATH = Path(__file__).parent / ".env"


@dataclass(frozen=True)
class Settings:
    postgres_host: str
    postgres_port: int
    postgres_user: str
    postgres_password: str
    postgres_db: str
    session_secret: str
    fernet_secret: str
    encryption_key: str


def get_settings() -> Settings:
    """Read PostgreSQL settings from api/.env. The file wins over existing variables."""
    load_dotenv(ENV_PATH, override=True)
    return Settings(
        postgres_host=os.environ.get("POSTGRES_HOST", "localhost"),
        postgres_port=int(os.environ.get("POSTGRES_PORT", "5432")),
        postgres_user=os.environ.get("POSTGRES_USER", "odp"),
        postgres_password=os.environ.get("POSTGRES_PASSWORD", "odp"),
        postgres_db=os.environ.get("POSTGRES_DB", "odp_platform"),
        session_secret=os.environ.get("SESSION_SECRET", "odp-local-session"),
        fernet_secret=os.environ.get("FERNET_SECRET", "default-secret-key-change-in-production"),
        encryption_key=os.environ.get("ENCRYPTION_KEY", ""),
    )
