from fastapi.testclient import TestClient

from api.errors import UsernameTaken
from api.main import app
from api.passwords import hash_password
from api.responses import FIELD_TOO_LONG, USERNAME_TAKEN


def test_password_hash_is_sha256_hex():
    import hashlib

    assert hash_password("admin") == hashlib.sha256(b"admin").hexdigest()


def test_register_stores_a_hash_and_not_the_password(monkeypatch):
    monkeypatch.setattr("api.registration.ensure_default_admin", lambda: None)
    stored = {}

    def insert(username, email, password_hash):
        stored["row"] = (username, email, password_hash)

    monkeypatch.setattr("api.registration.insert_user", insert)
    response = TestClient(app).post(
        "/register",
        json={"username": "ada", "email": "ada@example.com", "password": "secret"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "message": "User registered successfully",
    }
    assert stored["row"][0] == "ada"
    assert stored["row"][2] == hash_password("secret")
    assert "secret" not in response.text


def test_register_rejects_reserved_admin(monkeypatch):
    monkeypatch.setattr("api.registration.ensure_default_admin", lambda: None)
    called = {"insert": False}

    def insert(username, email, password_hash):
        called["insert"] = True

    monkeypatch.setattr("api.registration.insert_user", insert)
    response = TestClient(app).post(
        "/register",
        json={"username": "Admin", "email": "a@example.com", "password": "x"},
    )
    assert response.status_code == 400
    assert response.json()["status"] == "error"
    assert "reserved" in response.json()["message"]
    assert called["insert"] is False


def test_register_rejects_a_duplicate_username(monkeypatch):
    monkeypatch.setattr("api.registration.ensure_default_admin", lambda: None)

    def insert(username, email, password_hash):
        raise UsernameTaken()

    monkeypatch.setattr("api.registration.insert_user", insert)
    response = TestClient(app).post(
        "/register",
        json={"username": "ada", "email": "a@example.com", "password": "x"},
    )
    assert response.status_code == 409
    assert response.json() == {"status": "error", "message": USERNAME_TAKEN}


def test_register_rejects_a_long_username(monkeypatch):
    monkeypatch.setattr("api.registration.ensure_default_admin", lambda: None)
    response = TestClient(app).post(
        "/register",
        json={"username": "a" * 33, "email": "a@example.com", "password": "x"},
    )
    assert response.status_code == 400
    assert response.json()["message"] == FIELD_TOO_LONG


def test_register_survives_a_database_close_after_commit(monkeypatch):
    import psycopg

    from api.user_sql import ensure_default_admin, insert_user

    class Conn:
        def __init__(self):
            self.committed = False

        def execute(self, query, params=None):
            return self

        def commit(self):
            self.committed = True

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            if self.committed:
                raise psycopg.OperationalError("connection closed")
            return False

    monkeypatch.setattr("api.user_sql.connect", lambda: Conn())
    ensure_default_admin()
    insert_user("ada", "ada@example.com", "hash")


def test_a_duplicate_username_stays_taken_when_the_connection_closes(monkeypatch):
    import psycopg

    from api.user_sql import insert_user

    class Conn:
        def execute(self, query, params=None):
            raise psycopg.errors.UniqueViolation("duplicate")

        def rollback(self):
            return None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            raise psycopg.OperationalError("connection closed")

    monkeypatch.setattr("api.user_sql.connect", lambda: Conn())
    try:
        insert_user("ada", "ada@example.com", "hash")
    except UsernameTaken:
        pass
    else:
        raise AssertionError("expected UsernameTaken")
