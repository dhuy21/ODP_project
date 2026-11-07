from fastapi.testclient import TestClient

from api.auth import authenticate
from api.main import app
from api.passwords import hash_password
from api.responses import AUTH_REQUIRED, INVALID_CREDENTIALS


def test_authenticate_checks_the_hash(monkeypatch):
    monkeypatch.setattr(
        "api.auth.find_user_credentials",
        lambda username: {
            "username": username,
            "password_hash": hash_password("right"),
            "role": "user",
        },
    )
    assert authenticate("ada", "wrong") is None
    assert authenticate("missing", "right")["role"] == "user"


def test_authenticate_hides_unknown_users(monkeypatch):
    monkeypatch.setattr("api.auth.find_user_credentials", lambda username: None)
    assert authenticate("missing", "right") is None


def test_authenticate_rejects_a_non_string_hash(monkeypatch):
    monkeypatch.setattr(
        "api.auth.find_user_credentials",
        lambda username: {"username": username, "password_hash": None, "role": "user"},
    )
    assert authenticate("ada", "right") is None


def test_login_ensures_the_default_admin(monkeypatch):
    called = {"n": 0}

    def ensure():
        called["n"] += 1

    monkeypatch.setattr("api.main.ensure_default_admin", ensure)
    monkeypatch.setattr(
        "api.main.authenticate",
        lambda username, password: {"username": "admin", "role": "admin"},
    )
    response = TestClient(app).post(
        "/login",
        json={"username": "admin", "password": "admin"},
    )
    assert response.status_code == 200
    assert called["n"] == 1


def test_login_sets_a_session_cookie(monkeypatch):
    monkeypatch.setattr("api.main.ensure_default_admin", lambda: None)
    monkeypatch.setattr(
        "api.main.authenticate",
        lambda username, password: {"username": username, "role": "admin"},
    )
    response = TestClient(app).post(
        "/login",
        json={"username": "admin", "password": "admin"},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "success", "user": "admin", "role": "admin"}
    assert "session" in response.cookies
    assert "password" not in response.text


def test_login_rejects_bad_credentials_without_a_cookie(monkeypatch):
    monkeypatch.setattr("api.main.ensure_default_admin", lambda: None)
    monkeypatch.setattr("api.main.authenticate", lambda username, password: None)
    response = TestClient(app).post(
        "/login",
        json={"username": "ada", "password": "nope"},
    )
    assert response.status_code == 401
    assert response.json() == {"status": "error", "message": INVALID_CREDENTIALS}
    assert "session" not in response.cookies
    assert "nope" not in response.text


def test_logout_clears_the_session_cookie(monkeypatch):
    monkeypatch.setattr("api.main.ensure_default_admin", lambda: None)
    monkeypatch.setattr(
        "api.main.authenticate",
        lambda username, password: {"username": username, "role": "user"},
    )
    client = TestClient(app)
    login = client.post("/login", json={"username": "ada", "password": "secret"})
    assert "session" in login.cookies
    logout = client.post("/logout")
    assert logout.status_code == 200
    assert logout.json() == {"status": "success"}
    assert client.cookies.get("session") in (None, "")


def test_logout_closes_that_users_terminals(monkeypatch):
    seen = {}

    async def close(username):
        seen["username"] = username

    monkeypatch.setattr("api.main.close_user_terminals", close)
    monkeypatch.setattr("api.main.ensure_default_admin", lambda: None)
    monkeypatch.setattr(
        "api.main.authenticate",
        lambda username, password: {"username": username, "role": "user"},
    )
    client = TestClient(app)
    client.post("/login", json={"username": "ada", "password": "secret"})
    logout = client.post("/logout")
    assert logout.status_code == 200
    assert seen == {"username": "ada"}


def test_logout_without_a_session_is_success():
    response = TestClient(app).post("/logout")
    assert response.status_code == 200
    assert response.json() == {"status": "success"}


def test_session_requires_a_signed_in_user():
    response = TestClient(app).get("/session")
    assert response.status_code == 401
    assert response.json()["message"] == AUTH_REQUIRED


def test_session_returns_the_database_role(monkeypatch):
    monkeypatch.setattr("api.main.ensure_default_admin", lambda: None)
    monkeypatch.setattr(
        "api.main.authenticate",
        lambda username, password: {"username": "ada", "role": "user"},
    )
    monkeypatch.setattr("api.main.find_user_role", lambda username: "admin")
    client = TestClient(app)
    client.post("/login", json={"username": "ada", "password": "secret"})
    response = client.get("/session")
    assert response.status_code == 200
    assert response.json() == {"status": "success", "user": "ada", "role": "admin"}
    assert "secret" not in response.text


def test_session_clears_a_deleted_account(monkeypatch):
    monkeypatch.setattr("api.main.ensure_default_admin", lambda: None)
    monkeypatch.setattr(
        "api.main.authenticate",
        lambda username, password: {"username": "ada", "role": "user"},
    )
    monkeypatch.setattr("api.main.find_user_role", lambda username: None)
    client = TestClient(app)
    client.post("/login", json={"username": "ada", "password": "secret"})
    response = client.get("/session")
    assert response.status_code == 401
    again = client.get("/session")
    assert again.status_code == 401
