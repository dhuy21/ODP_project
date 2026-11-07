import hashlib
import re
from pathlib import Path

from api.db import connect

MIGRATIONS = Path(__file__).resolve().parents[1] / "database" / "postgres"
MIGRATION_NAME = re.compile(r"^(\d{3})_.+\.sql$")


def file_checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_recorded(filename: str, recorded: str | None, current: str) -> str | None:
    """Return a checksum to store when the old row has none.

    Raise when an applied file was edited. Return None when the stored checksum matches.
    """
    if recorded is None:
        return current
    if recorded != current:
        raise RuntimeError(
            f"{filename} changed after it was applied. "
            "Add a new numbered SQL file instead of editing this one."
        )
    return None


def applied_rows(conn) -> dict[str, str | None]:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            filename TEXT PRIMARY KEY,
            checksum TEXT,
            applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        ALTER TABLE schema_migrations
        ADD COLUMN IF NOT EXISTS checksum TEXT
        """
    )
    rows = conn.execute("SELECT filename, checksum FROM schema_migrations").fetchall()
    return {row["filename"]: row["checksum"] for row in rows}


def mark_applied(conn, filename: str, checksum: str) -> None:
    conn.execute(
        "INSERT INTO schema_migrations (filename, checksum) VALUES (%s, %s)",
        (filename, checksum),
    )


def migration_files() -> list[Path]:
    if not MIGRATIONS.is_dir():
        raise FileNotFoundError(f"Migration directory not found: {MIGRATIONS}")
    found = [path for path in MIGRATIONS.glob("*.sql") if path.is_file()]
    if not found:
        raise FileNotFoundError(f"No migration files in {MIGRATIONS}")
    numbered: list[tuple[int, str, Path]] = []
    seen: set[int] = set()
    for path in found:
        match = MIGRATION_NAME.match(path.name)
        if match is None:
            raise ValueError(
                f"{path.name} must look like 001_description.sql so files run in numeric order."
            )
        number = int(match.group(1))
        if number in seen:
            raise ValueError(f"Two migration files use number {number:03d}.")
        seen.add(number)
        numbered.append((number, path.name, path))
    return [path for _, _, path in sorted(numbered)]


def apply_pending() -> list[str]:
    """Apply numbered SQL files that are not yet recorded. Return the names applied."""
    files = migration_files()
    applied_now = []
    with connect() as conn:
        done = applied_rows(conn)
        for path in files:
            checksum = file_checksum(path)
            if path.name in done:
                fill = check_recorded(path.name, done[path.name], checksum)
                if fill is not None:
                    conn.execute(
                        "UPDATE schema_migrations SET checksum = %s WHERE filename = %s",
                        (fill, path.name),
                    )
                    applied_now.append(path.name + " checksum recorded")
                continue
            conn.execute(path.read_text(encoding="utf-8"))
            mark_applied(conn, path.name, checksum)
            applied_now.append(path.name)
        conn.commit()
    return applied_now


def main() -> None:
    names = apply_pending()
    if not names:
        print("No pending migrations.")
        return
    for name in names:
        print(f"Applied {name}")


if __name__ == "__main__":
    main()
