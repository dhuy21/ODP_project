import threading

from fastapi.testclient import TestClient

from api.expiry import expire_due, sleep_seconds
from api.main import app


def test_sleep_stays_between_one_and_thirty_seconds():
    assert sleep_seconds(None, 100) == 30
    assert sleep_seconds(105, 100) == 5
    assert sleep_seconds(1000, 100) == 30
    assert sleep_seconds(90, 100) == 1


def test_client_requests_do_not_start_the_expiry_thread():
    TestClient(app).get("/health")
    assert all(thread.name != "odp-expiry" for thread in threading.enumerate())


def test_expire_due_expires_only_the_due_reservation(monkeypatch):
    calls = []

    class Result:
        def __init__(self, row):
            self._row = row

        def fetchone(self):
            return self._row

    class Conn:
        def execute(self, query, params=None):
            calls.append((query, params))
            if "FOR UPDATE" in query:
                return Result(
                    {
                        "status": "active",
                        "expires_at": 50,
                        "nodes": [{"name": "pool-node-1"}, {"ip": "x"}],
                    }
                )
            return Result(None)

        def commit(self):
            calls.append(("COMMIT", None))

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        "api.expiry._due_reservations",
        lambda now: [{"id": "res-1", "username": "ada"}],
    )
    monkeypatch.setattr("api.expiry._free_orphans", lambda now: 0)
    monkeypatch.setattr("api.expiry.connect", lambda: Conn())
    monkeypatch.setattr(
        "api.node_cleanup.remove_container_user",
        lambda name, username: calls.append(("docker", name, username)),
    )
    assert expire_due(100) == 1
    sql_calls = [item for item in calls if len(item) == 2]
    assert ("docker", "pool-node-1", "ada") in calls
    updates = [params for query, params in sql_calls if query and "SET status = 'expired'" in query]
    frees = [params for query, params in sql_calls if query and "owner = %s" in query]
    assert updates == [("res-1",)]
    assert frees == [(["pool-node-1"], "ada")]
    docker_at = calls.index(("docker", "pool-node-1", "ada"))
    free_at = next(
        i for i, item in enumerate(calls) if len(item) == 2 and item[0] and "owner = %s" in item[0]
    )
    assert docker_at < free_at


def test_skipping_a_reservation_survives_a_database_close(monkeypatch):
    import psycopg

    from api.expiry import _expire_one

    class Conn:
        def execute(self, query, params=None):
            return self

        def fetchone(self):
            return {"status": "released", "expires_at": 1, "nodes": []}

        def rollback(self):
            return None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            raise psycopg.OperationalError("connection closed")

    monkeypatch.setattr("api.expiry.connect", lambda: Conn())
    assert _expire_one("res-1", "ada", 100) is False
