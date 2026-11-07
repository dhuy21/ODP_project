from fastapi.testclient import TestClient

from api.errors import ReservationMissing, ReservationNotActive
from api.main import app
from api.releasing import release_reservation
from api.responses import (
    AUTH_REQUIRED,
    RESERVATION_NOT_ACTIVE,
    RESERVATION_NOT_FOUND,
    RESOURCES_RELEASED,
)


def _login(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("api.main.ensure_default_admin", lambda: None)
    monkeypatch.setattr(
        "api.main.authenticate",
        lambda username, password: {"username": "ada", "role": "user"},
    )
    client.post("/login", json={"username": "ada", "password": "secret"})


def test_release_requires_a_session():
    response = TestClient(app).post("/reservations/res-1/release")
    assert response.status_code == 401
    assert response.json()["message"] == AUTH_REQUIRED


def test_release_of_someone_elses_reservation_is_not_found(monkeypatch):
    client = TestClient(app)
    _login(client, monkeypatch)

    def missing(username, reservation_id):
        assert username == "ada"
        assert reservation_id == "res-1"
        raise ReservationMissing()

    monkeypatch.setattr("api.main.release_reservation", missing)
    response = client.post("/reservations/res-1/release")
    assert response.status_code == 404
    assert response.json()["message"] == RESERVATION_NOT_FOUND


def test_release_of_an_inactive_reservation_does_not_free_nodes(monkeypatch):
    client = TestClient(app)
    _login(client, monkeypatch)
    monkeypatch.setattr(
        "api.main.release_reservation",
        lambda username, reservation_id: (_ for _ in ()).throw(ReservationNotActive()),
    )
    response = client.post("/reservations/res-1/release")
    assert response.status_code == 409
    assert response.json()["message"] == RESERVATION_NOT_ACTIVE


def test_release_success_has_no_password(monkeypatch):
    client = TestClient(app)
    _login(client, monkeypatch)
    monkeypatch.setattr("api.main.release_reservation", lambda username, reservation_id: None)
    response = client.post("/reservations/res-1/release")
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": RESOURCES_RELEASED}


class _Result:
    def __init__(self, row=None, rowcount=1):
        self._row = row
        self.rowcount = rowcount

    def fetchone(self):
        return self._row


class _Conn:
    def __init__(self, row):
        self.row = row
        self.calls = []
        self.committed = False

    def execute(self, query, params=None):
        self.calls.append((query, params))
        if "FOR UPDATE" in query:
            return _Result(self.row)
        return _Result()

    def commit(self):
        self.committed = True

    def rollback(self):
        self.calls.append(("ROLLBACK", None))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_release_cleans_containers_before_freeing_only_that_owner(monkeypatch):
    conn = _Conn(
        {
            "status": "active",
            "nodes": [{"name": "pool-node-1", "ip": "172.30.0.2", "port": 3000}, {"ip": "x"}],
        }
    )
    cleaned = []
    monkeypatch.setattr("api.releasing.connect", lambda: conn)
    monkeypatch.setattr(
        "api.node_cleanup.remove_container_user",
        lambda name, username: cleaned.append((name, username)),
    )
    release_reservation("ada", "res-1")
    assert cleaned == [("pool-node-1", "ada")]
    assert conn.committed
    select, free, status = conn.calls
    assert "vm_password" not in select[0]
    assert free[1] == (["pool-node-1"], "ada")
    assert "owner = %s" in free[0]
    assert status[1] == ("res-1",)
    assert conn.calls.index(free) > 0
    assert cleaned


def test_inactive_row_does_not_touch_containers(monkeypatch):
    conn = _Conn({"status": "released", "nodes": [{"name": "pool-node-1"}]})
    cleaned = []
    monkeypatch.setattr("api.releasing.connect", lambda: conn)
    monkeypatch.setattr(
        "api.node_cleanup.remove_container_user",
        lambda name, username: cleaned.append(name),
    )
    try:
        release_reservation("ada", "res-1")
    except ReservationNotActive:
        pass
    else:
        raise AssertionError("expected ReservationNotActive")
    assert cleaned == []
    assert conn.committed is False
    assert conn.calls[-1] == ("ROLLBACK", None)


def test_close_keeps_a_missing_or_inactive_result(monkeypatch):
    import psycopg

    class ClosingConn(_Conn):
        def __exit__(self, exc_type, exc, tb):
            raise psycopg.OperationalError("connection closed")

    monkeypatch.setattr("api.node_cleanup.remove_container_user", lambda name, username: None)
    monkeypatch.setattr("api.releasing.connect", lambda: ClosingConn(None))
    try:
        release_reservation("ada", "missing")
    except ReservationMissing:
        pass
    else:
        raise AssertionError("expected ReservationMissing")

    monkeypatch.setattr(
        "api.releasing.connect",
        lambda: ClosingConn({"status": "released", "nodes": []}),
    )
    try:
        release_reservation("ada", "old")
    except ReservationNotActive:
        pass
    else:
        raise AssertionError("expected ReservationNotActive")


def test_database_close_after_release_commit_is_success(monkeypatch):
    import psycopg

    class ClosingConn(_Conn):
        def __exit__(self, exc_type, exc, tb):
            if self.committed:
                raise psycopg.OperationalError("connection closed")
            return False

    conn = ClosingConn({"status": "active", "nodes": [{"name": "pool-node-1"}]})
    monkeypatch.setattr("api.releasing.connect", lambda: conn)
    monkeypatch.setattr("api.node_cleanup.remove_container_user", lambda name, username: None)
    release_reservation("ada", "res-1")
    assert conn.committed


def test_missing_container_does_not_raise(monkeypatch):
    import docker

    from api.containers import remove_container_user

    class Containers:
        def get(self, name):
            raise docker.errors.NotFound("missing")

    class Client:
        containers = Containers()

        def close(self):
            return None

    monkeypatch.setattr(docker, "from_env", lambda: Client())
    remove_container_user("pool-node-1", "ada")
