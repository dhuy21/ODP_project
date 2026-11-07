import psycopg
import pytest

from api.errors import DatabaseUnavailable
from api.pool_sql import get_pool_status, list_pool_nodes
from api.reservation_sql import get_reservation, list_user_reservations, public_reservation


def test_connection_failure_is_database_unavailable(monkeypatch):
    def fail():
        raise psycopg.OperationalError("password=secret")

    monkeypatch.setattr("api.db.connect", fail)
    with pytest.raises(DatabaseUnavailable):
        get_pool_status()
    with pytest.raises(DatabaseUnavailable):
        list_pool_nodes()
    with pytest.raises(DatabaseUnavailable):
        list_user_reservations("anyone")
    with pytest.raises(DatabaseUnavailable):
        get_reservation("missing")


def test_read_survives_a_database_close_after_fetch(monkeypatch):
    class Conn:
        def execute(self, query, params=None):
            return self

        def fetchall(self):
            return [{"total": 1}]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            raise psycopg.OperationalError("connection closed")

    monkeypatch.setattr("api.db.connect", lambda: Conn())
    from api.db import fetch_all

    assert fetch_all("SELECT 1") == [{"total": 1}]


def test_public_reservation_hides_password_and_fills_empty_json():
    row = {
        "id": "res-1",
        "vm_count": 2,
        "duration_minutes": 30,
        "status": "active",
        "created_at": 1,
        "expires_at": 2,
        "nodes": None,
        "final_stats": None,
        "packages": None,
        "vm_password_encrypted": "secret",
    }
    result = public_reservation(row, "ada")
    assert result["username"] == "ada"
    assert result["nodes"] == []
    assert result["final_stats"] == {}
    assert result["packages"] == []
    assert "vm_password_encrypted" not in result
    assert "secret" not in str(result)


def test_reservation_queries_do_not_select_the_password(monkeypatch):
    seen = []

    def fake(query, params=None):
        seen.append(query)
        return []

    monkeypatch.setattr("api.reservation_sql.fetch_all", fake)
    list_user_reservations("ada")
    get_reservation("res-1")
    assert seen
    assert all("vm_password" not in query for query in seen)
