from fastapi.testclient import TestClient

import pytest

from api.errors import DatabaseUnavailable
from api.main import app
from api.responses import DATABASE_UNAVAILABLE, RESERVATION_NOT_FOUND


def test_health():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_pool_status_when_database_is_down(monkeypatch):
    def fail():
        raise DatabaseUnavailable("password=secret connection refused")

    monkeypatch.setattr("api.main.get_pool_status", fail)
    response = TestClient(app).get("/pool/status")
    assert response.status_code == 503
    assert response.json() == {"status": "error", "message": DATABASE_UNAVAILABLE}
    assert "password" not in response.text


def test_pool_nodes_returns_sql_rows(monkeypatch):
    monkeypatch.setattr(
        "api.main.list_pool_nodes",
        lambda: [
            {
                "name": "pool-node-1",
                "ip": "172.30.0.2",
                "port": 3000,
                "status": "free",
                "owner": None,
                "expiry": 0.0,
            }
        ],
    )
    response = TestClient(app).get("/pool/nodes")
    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "nodes": [
            {
                "name": "pool-node-1",
                "ip": "172.30.0.2",
                "port": 3000,
                "status": "free",
                "owner": None,
                "expiry": 0.0,
            }
        ],
    }


def test_pool_nodes_when_database_is_down(monkeypatch):
    def fail():
        raise DatabaseUnavailable("password=secret")

    monkeypatch.setattr("api.main.list_pool_nodes", fail)
    response = TestClient(app).get("/pool/nodes")
    assert response.status_code == 503
    assert response.json()["message"] == DATABASE_UNAVAILABLE
    assert "password" not in response.text


def test_user_reservations_omit_the_machine_password(monkeypatch):
    monkeypatch.setattr(
        "api.main.list_user_reservations",
        lambda username: [
            {
                "id": "res-1",
                "username": username,
                "vm_count": 1,
                "duration_minutes": 60,
                "status": "active",
                "created_at": 1.0,
                "expires_at": 2.0,
                "nodes": [],
                "final_stats": {},
                "packages": [],
            }
        ],
    )
    response = TestClient(app).get("/users/ada/reservations")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["reservations"][0]["username"] == "ada"
    assert "vm_password_encrypted" not in body["reservations"][0]
    assert "password" not in response.text


def test_unknown_user_has_an_empty_reservation_list(monkeypatch):
    monkeypatch.setattr("api.main.list_user_reservations", lambda username: [])
    response = TestClient(app).get("/users/missing/reservations")
    assert response.status_code == 200
    assert response.json() == {"status": "success", "reservations": []}


def test_reservation_detail_omits_the_machine_password(monkeypatch):
    monkeypatch.setattr(
        "api.main.get_reservation",
        lambda reservation_id: {
            "id": reservation_id,
            "username": "ada",
            "vm_count": 1,
            "duration_minutes": 60,
            "status": "active",
            "created_at": 1.0,
            "expires_at": 2.0,
            "nodes": [],
            "final_stats": {},
            "packages": [],
        },
    )
    response = TestClient(app).get("/reservations/res-1")
    assert response.status_code == 200
    reservation = response.json()["reservation"]
    assert reservation["id"] == "res-1"
    assert "vm_password_encrypted" not in reservation
    assert "password" not in response.text


def test_missing_reservation_is_not_found(monkeypatch):
    monkeypatch.setattr("api.main.get_reservation", lambda reservation_id: None)
    response = TestClient(app).get("/reservations/missing")
    assert response.status_code == 404
    assert response.json() == {"status": "error", "message": RESERVATION_NOT_FOUND}


def test_pool_status_does_not_hide_programming_errors(monkeypatch):
    def fail():
        raise RuntimeError("sql bug")

    monkeypatch.setattr("api.main.get_pool_status", fail)
    with pytest.raises(RuntimeError, match="sql bug"):
        TestClient(app).get("/pool/status")
