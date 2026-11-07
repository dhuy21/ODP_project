import pytest

from api.migrate import apply_pending, check_recorded, migration_files
from api.settings import get_settings


def test_edited_migration_is_rejected():
    with pytest.raises(RuntimeError, match="changed after it was applied"):
        check_recorded("001_init.sql", "old-checksum", "new-checksum")


def test_missing_checksum_can_be_filled():
    assert check_recorded("001_init.sql", None, "abc") == "abc"


def test_matching_checksum_needs_no_write():
    assert check_recorded("001_init.sql", "abc", "abc") is None


def test_env_file_overrides_existing_variables(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "POSTGRES_HOST=from-file\nPOSTGRES_PORT=5433\n"
        "POSTGRES_USER=file-user\nPOSTGRES_PASSWORD=file-pass\nPOSTGRES_DB=file-db\n",
        encoding="utf-8",
    )
    for key in (
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
    ):
        monkeypatch.setenv(key, "from-shell")
    monkeypatch.setattr("api.settings.ENV_PATH", env_file)
    settings = get_settings()
    assert settings.postgres_host == "from-file"
    assert settings.postgres_port == 5433
    assert settings.postgres_db == "file-db"


def test_migration_names_must_be_numbered(monkeypatch, tmp_path):
    (tmp_path / "init.sql").write_text("SELECT 1;\n", encoding="utf-8")
    monkeypatch.setattr("api.migrate.MIGRATIONS", tmp_path)
    with pytest.raises(ValueError, match="001_description.sql"):
        migration_files()


def test_migrations_run_in_numeric_order(monkeypatch, tmp_path):
    (tmp_path / "010_later.sql").write_text("SELECT 1;\n", encoding="utf-8")
    (tmp_path / "002_earlier.sql").write_text("SELECT 1;\n", encoding="utf-8")
    monkeypatch.setattr("api.migrate.MIGRATIONS", tmp_path)
    assert [path.name for path in migration_files()] == ["002_earlier.sql", "010_later.sql"]


def test_empty_migration_directory_fails(monkeypatch, tmp_path):
    monkeypatch.setattr("api.migrate.MIGRATIONS", tmp_path)
    with pytest.raises(FileNotFoundError, match="No migration files"):
        migration_files()


def test_duplicate_migration_number_is_rejected(monkeypatch, tmp_path):
    (tmp_path / "001_one.sql").write_text("SELECT 1;\n", encoding="utf-8")
    (tmp_path / "001_two.sql").write_text("SELECT 1;\n", encoding="utf-8")
    monkeypatch.setattr("api.migrate.MIGRATIONS", tmp_path)
    with pytest.raises(ValueError, match="number 001"):
        migration_files()


def test_missing_migration_directory_fails_before_connecting(monkeypatch, tmp_path):
    monkeypatch.setattr("api.migrate.MIGRATIONS", tmp_path / "missing")
    with pytest.raises(FileNotFoundError):
        migration_files()
    with pytest.raises(FileNotFoundError):
        apply_pending()
