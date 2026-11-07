import psycopg
import pytest
from fastapi.testclient import TestClient

from api.errors import DatabaseUnavailable
from api.main import app
from api.reservation_sql import list_all_reservations
from api.releasing import delete_account, delete_reservation
from api.responses import (
    ADMIN_REQUIRED,
    AUTH_REQUIRED,
    CANNOT_DELETE_ADMIN,
    CANNOT_DELETE_SYSTEM_ADMIN,
    CANNOT_DEMOTE_ADMIN,
    INVALID_ROLE,
    POOL_RECOVER_FAILED,
    RESERVATION_DELETED,
    RESERVATION_NOT_FOUND,
    SYSTEM_ADMIN_ROLE,
    USER_NOT_FOUND,
)
from api.user_sql import list_users, set_user_role


def _login(client: TestClient, monkeypatch, username: str = "ada") -> None:
    monkeypatch.setattr("api.main.ensure_default_admin", lambda: None)
    monkeypatch.setattr(
        "api.main.authenticate",
        lambda user, password: {"username": username, "role": "user"},
    )
    client.post("/login", json={"username": username, "password": "secret"})


def test_admin_users_requires_a_session():
    response = TestClient(app).get("/admin/users")
    assert response.status_code == 401
    assert response.json()["message"] == AUTH_REQUIRED


def test_a_normal_user_cannot_list_accounts(monkeypatch):
    client = TestClient(app)
    _login(client, monkeypatch)
    monkeypatch.setattr("api.auth.find_user_role", lambda username: "user")
    response = client.get("/admin/users")
    assert response.status_code == 403
    assert response.json() == {"status": "error", "message": ADMIN_REQUIRED}
    assert "password" not in response.text


def test_admin_lists_accounts_from_the_database_role(monkeypatch):
    client = TestClient(app)
    _login(client, monkeypatch, username="admin")
    monkeypatch.setattr("api.auth.find_user_role", lambda username: "admin")
    monkeypatch.setattr(
        "api.main.list_users",
        lambda: [
            {
                "username": "admin",
                "email": "admin@iac.com",
                "role": "admin",
                "created_at": "2026-01-01T00:00:00",
                "reservation_count": 0,
            }
        ],
    )
    response = client.get("/admin/users")
    assert response.status_code == 200
    assert response.json()["users"][0]["username"] == "admin"
    assert "password" not in response.text


def test_a_deleted_account_loses_the_admin_session(monkeypatch):
    client = TestClient(app)
    _login(client, monkeypatch, username="admin")
    monkeypatch.setattr("api.auth.find_user_role", lambda username: None)
    response = client.get("/admin/users")
    assert response.status_code == 401
    monkeypatch.setattr("api.auth.find_user_role", lambda username: "admin")
    assert client.get("/admin/users").status_code == 401


def test_list_users_does_not_select_the_password(monkeypatch):
    seen = []

    def fake(query, params=None):
        seen.append(query)
        return [
            {
                "username": "ada",
                "email": "ada@example.com",
                "role": "user",
                "created_at": None,
                "reservation_count": 2,
            }
        ]

    monkeypatch.setattr("api.user_sql.fetch_all", fake)
    users = list_users()
    assert "password" not in seen[0]
    assert users == [
        {
            "username": "ada",
            "email": "ada@example.com",
            "role": "user",
            "created_at": "",
            "reservation_count": 2,
        }
    ]


def test_admin_reservations_requires_a_session():
    response = TestClient(app).get("/admin/reservations")
    assert response.status_code == 401
    assert response.json()["message"] == AUTH_REQUIRED


def test_a_normal_user_cannot_list_every_reservation(monkeypatch):
    client = TestClient(app)
    _login(client, monkeypatch)
    monkeypatch.setattr("api.auth.find_user_role", lambda username: "user")
    response = client.get("/admin/reservations")
    assert response.status_code == 403
    assert response.json()["message"] == ADMIN_REQUIRED


def test_admin_lists_every_reservation_without_a_password(monkeypatch):
    client = TestClient(app)
    _login(client, monkeypatch, username="admin")
    monkeypatch.setattr("api.auth.find_user_role", lambda username: "admin")
    monkeypatch.setattr(
        "api.main.list_all_reservations",
        lambda: [{"id": "res-1", "username": "ada", "status": "active"}],
    )
    response = client.get("/admin/reservations")
    assert response.status_code == 200
    assert response.json()["reservations"][0]["id"] == "res-1"
    assert "password" not in response.text


def test_list_all_reservations_does_not_select_the_password(monkeypatch):
    seen = []

    def fake(query, params=None):
        seen.append(query)
        return [
            {
                "id": "res-1",
                "username": "ada",
                "vm_count": 1,
                "duration_minutes": 60,
                "status": "active",
                "created_at": 10,
                "expires_at": 20,
                "nodes": None,
                "final_stats": None,
                "packages": ["htop"],
                "vm_password_encrypted": "secret-token",
            }
        ]

    monkeypatch.setattr("api.reservation_sql.fetch_all", fake)
    reservations = list_all_reservations()
    assert "vm_password" not in seen[0]
    assert reservations[0]["username"] == "ada"
    assert reservations[0]["packages"] == ["htop"]
    assert "password" not in reservations[0]
    assert "secret-token" not in str(reservations[0])


def test_admin_overview_requires_a_session():
    response = TestClient(app).get("/admin/overview")
    assert response.status_code == 401
    assert response.json()["message"] == AUTH_REQUIRED


def test_a_normal_user_cannot_read_the_overview(monkeypatch):
    client = TestClient(app)
    _login(client, monkeypatch)
    monkeypatch.setattr("api.auth.find_user_role", lambda username: "user")
    response = client.get("/admin/overview")
    assert response.status_code == 403
    assert response.json()["message"] == ADMIN_REQUIRED


def test_admin_overview_uses_database_counts(monkeypatch):
    client = TestClient(app)
    _login(client, monkeypatch, username="admin")
    monkeypatch.setattr("api.auth.find_user_role", lambda username: "admin")
    monkeypatch.setattr(
        "api.main.count_users_by_role",
        lambda: {"total_users": 4, "admin_count": 1, "user_count": 3},
    )
    monkeypatch.setattr("api.main.count_active_reservations", lambda: 2)
    monkeypatch.setattr(
        "api.main.get_pool_status",
        lambda: {"total": 30, "free": 28, "allocated": 2},
    )
    response = client.get("/admin/overview")
    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "total_users": 4,
        "admin_count": 1,
        "user_count": 3,
        "active_reservations": 2,
        "total_containers": 30,
        "available_containers": 28,
    }


def test_admin_pool_requires_a_session():
    response = TestClient(app).get("/admin/pool")
    assert response.status_code == 401
    assert response.json()["message"] == AUTH_REQUIRED


def test_a_normal_user_cannot_read_the_admin_pool(monkeypatch):
    client = TestClient(app)
    _login(client, monkeypatch)
    monkeypatch.setattr("api.auth.find_user_role", lambda username: "user")
    response = client.get("/admin/pool")
    assert response.status_code == 403
    assert response.json()["message"] == ADMIN_REQUIRED


def test_admin_pool_reads_sql_without_docker(monkeypatch):
    client = TestClient(app)
    _login(client, monkeypatch, username="admin")
    monkeypatch.setattr("api.auth.find_user_role", lambda username: "admin")
    monkeypatch.setattr(
        "api.main.list_pool_nodes",
        lambda: [
            {
                "name": "pool-node-1",
                "ip": "172.30.0.2",
                "port": 3000,
                "status": "free",
                "owner": None,
                "expiry": 0,
            }
        ],
    )
    response = client.get("/admin/pool")
    assert response.status_code == 200
    assert response.json()["nodes"][0]["name"] == "pool-node-1"
    assert "password" not in response.text


def test_admin_create_user_requires_a_session():
    response = TestClient(app).post(
        "/admin/users",
        json={"username": "ada", "email": "ada@example.com", "password": "secret-pass"},
    )
    assert response.status_code == 401
    assert response.json()["message"] == AUTH_REQUIRED


def test_a_normal_user_cannot_create_an_account(monkeypatch):
    client = TestClient(app)
    _login(client, monkeypatch)
    monkeypatch.setattr("api.auth.find_user_role", lambda username: "user")
    response = client.post(
        "/admin/users",
        json={"username": "ada", "email": "ada@example.com", "password": "secret-pass"},
    )
    assert response.status_code == 403
    assert response.json()["message"] == ADMIN_REQUIRED
    assert "secret-pass" not in response.text


def test_admin_creates_a_user_through_the_register_rules(monkeypatch):
    client = TestClient(app)
    _login(client, monkeypatch, username="admin")
    monkeypatch.setattr("api.auth.find_user_role", lambda username: "admin")
    seen = {}

    def register(username, email, password):
        seen["args"] = (username, email, password)

    monkeypatch.setattr("api.main.register_user", register)
    response = client.post(
        "/admin/users",
        json={
            "username": "ada",
            "email": "ada@example.com",
            "password": "secret-pass",
            "role": "admin",
        },
    )
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "User registered successfully"}
    assert seen["args"] == ("ada", "ada@example.com", "secret-pass")
    assert "secret-pass" not in response.text


def _as_admin(client: TestClient, monkeypatch) -> None:
    _login(client, monkeypatch, username="admin")
    monkeypatch.setattr("api.auth.find_user_role", lambda username: "admin")


def test_role_change_rejects_an_unknown_role(monkeypatch):
    client = TestClient(app)
    _as_admin(client, monkeypatch)
    response = client.put("/admin/users/ada/role", json={"role": "owner"})
    assert response.status_code == 400
    assert response.json()["message"] == INVALID_ROLE


def test_the_system_admin_role_cannot_change(monkeypatch):
    client = TestClient(app)
    _as_admin(client, monkeypatch)
    response = client.put("/admin/users/admin/role", json={"role": "user"})
    assert response.status_code == 400
    assert response.json()["message"] == SYSTEM_ADMIN_ROLE


def test_a_missing_account_cannot_change_role(monkeypatch):
    client = TestClient(app)
    _as_admin(client, monkeypatch)

    def role_of(username: str):
        return "admin" if username == "admin" else None

    monkeypatch.setattr("api.auth.find_user_role", role_of)
    monkeypatch.setattr("api.main.set_user_role", lambda username, role: "missing")
    response = client.put("/admin/users/missing/role", json={"role": "admin"})
    assert response.status_code == 404
    assert response.json()["message"] == USER_NOT_FOUND


def test_another_admin_cannot_be_demoted(monkeypatch):
    client = TestClient(app)
    _as_admin(client, monkeypatch)
    monkeypatch.setattr("api.main.set_user_role", lambda username, role: "protected")
    response = client.put("/admin/users/other/role", json={"role": "user"})
    assert response.status_code == 400
    assert response.json()["message"] == CANNOT_DEMOTE_ADMIN


def test_a_locked_admin_is_not_demoted(monkeypatch):
    class Conn:
        def __init__(self):
            self.queries = []

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query, params=None):
            self.queries.append(query)

            class Result:
                def fetchone(self):
                    return {"id": 2, "role": "admin"}

            return Result()

        def rollback(self):
            self.queries.append("rollback")

        def commit(self):
            raise AssertionError("an admin was demoted")

    conn = Conn()
    monkeypatch.setattr("api.user_sql.connect", lambda: conn)
    assert set_user_role("other", "user") == "protected"
    assert not any(query.startswith("UPDATE") for query in conn.queries)


def test_a_role_change_database_failure_is_not_a_missing_user(monkeypatch):
    def down():
        raise psycopg.OperationalError("down")

    monkeypatch.setattr("api.user_sql.connect", down)
    with pytest.raises(DatabaseUnavailable):
        set_user_role("ada", "admin")


def test_admin_promotes_a_user(monkeypatch):
    client = TestClient(app)
    _as_admin(client, monkeypatch)
    monkeypatch.setattr("api.main.find_user_role", lambda username: "user")
    seen = {}
    monkeypatch.setattr(
        "api.main.set_user_role",
        lambda username, role: seen.update(username=username, role=role) or "updated",
    )
    response = client.put("/admin/users/ada/role", json={"role": "admin"})
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Role updated to admin"}
    assert seen == {"username": "ada", "role": "admin"}


def test_deleting_a_reservation_requires_a_session():
    response = TestClient(app).delete("/admin/reservations/res-1")
    assert response.status_code == 401
    assert response.json()["message"] == AUTH_REQUIRED


def test_a_normal_user_cannot_delete_a_reservation(monkeypatch):
    client = TestClient(app)
    _login(client, monkeypatch)
    monkeypatch.setattr("api.auth.find_user_role", lambda username: "user")
    response = client.delete("/admin/reservations/res-1")
    assert response.status_code == 403
    assert response.json()["message"] == ADMIN_REQUIRED


def test_admin_deletes_one_reservation(monkeypatch):
    client = TestClient(app)
    _login(client, monkeypatch, username="admin")
    monkeypatch.setattr("api.auth.find_user_role", lambda username: "admin")
    seen = {}
    monkeypatch.setattr(
        "api.main.delete_reservation",
        lambda reservation_id: seen.update(id=reservation_id),
    )
    response = client.delete("/admin/reservations/res-1")
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": RESERVATION_DELETED}
    assert seen["id"] == "res-1"


def test_delete_frees_only_that_reservations_nodes(monkeypatch):
    class Result:
        def __init__(self, row):
            self._row = row

        def fetchone(self):
            return self._row

    class Conn:
        def __init__(self):
            self.calls = []
            self.committed = False

        def execute(self, query, params=None):
            self.calls.append((query, params))
            if "FOR UPDATE" in query:
                return Result(
                    {
                        "username": "ada",
                        "nodes": [{"name": "pool-node-1"}, {"ip": "x"}],
                    }
                )
            return Result(None)

        def commit(self):
            self.committed = True

        def rollback(self):
            self.calls.append(("ROLLBACK", None))

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    conn = Conn()
    cleaned = []
    monkeypatch.setattr("api.releasing.connect", lambda: conn)
    monkeypatch.setattr(
        "api.node_cleanup.remove_container_user",
        lambda name, username: cleaned.append((name, username)),
    )
    delete_reservation("res-1")
    assert cleaned == [("pool-node-1", "ada")]
    assert conn.committed
    deleted = [params for query, params in conn.calls if query and "status = 'deleted'" in query]
    freed = [params for query, params in conn.calls if query and "owner = %s" in query]
    assert deleted == [("res-1",)]
    assert freed == [(["pool-node-1"], "ada")]
    assert "vm_password" not in conn.calls[0][0]


def test_delete_of_a_missing_reservation_is_not_found(monkeypatch):
    from api.errors import ReservationMissing

    def missing(reservation_id):
        raise ReservationMissing()

    client = TestClient(app)
    _login(client, monkeypatch, username="admin")
    monkeypatch.setattr("api.auth.find_user_role", lambda username: "admin")
    monkeypatch.setattr("api.main.delete_reservation", missing)
    response = client.delete("/admin/reservations/missing")
    assert response.status_code == 404
    assert response.json()["message"] == RESERVATION_NOT_FOUND


def test_deleting_the_system_admin_is_refused(monkeypatch):
    client = TestClient(app)
    _login(client, monkeypatch, username="admin")
    monkeypatch.setattr("api.auth.find_user_role", lambda username: "admin")
    response = client.delete("/admin/users/admin")
    assert response.status_code == 400
    assert response.json()["message"] == CANNOT_DELETE_SYSTEM_ADMIN


def test_another_admin_cannot_be_deleted(monkeypatch):
    client = TestClient(app)
    _login(client, monkeypatch, username="admin")
    monkeypatch.setattr("api.auth.find_user_role", lambda username: "admin")
    monkeypatch.setattr("api.main.delete_account", lambda username: ("admin", 0, 0))
    response = client.delete("/admin/users/other")
    assert response.status_code == 400
    assert response.json()["message"] == CANNOT_DELETE_ADMIN


def test_admin_deletes_a_user_and_reports_what_was_released(monkeypatch):
    client = TestClient(app)
    _login(client, monkeypatch, username="admin")
    monkeypatch.setattr("api.auth.find_user_role", lambda username: "admin")
    monkeypatch.setattr("api.main.delete_account", lambda username: ("deleted", 2, 1))
    response = client.delete("/admin/users/ada")
    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "message": "User ada deleted. Released 2 containers and 1 reservations.",
    }


def test_delete_account_frees_only_active_nodes_then_removes_the_user(monkeypatch):
    class Result:
        def __init__(self, row=None, rows=None):
            self._row = row
            self._rows = rows or []

        def fetchone(self):
            return self._row

        def fetchall(self):
            return self._rows

    class Conn:
        def __init__(self):
            self.calls = []
            self.committed = False

        def execute(self, query, params=None):
            self.calls.append((query, params))
            if "FROM users" in query:
                return Result(row={"id": 7, "role": "user"})
            if "status = 'active'" in query:
                return Result(
                    rows=[{"id": "res-1", "nodes": [{"name": "pool-node-1"}, {"ip": "x"}]}]
                )
            return Result()

        def commit(self):
            self.committed = True

        def rollback(self):
            self.calls.append(("ROLLBACK", None))

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    conn = Conn()
    cleaned = []
    monkeypatch.setattr("api.releasing.connect", lambda: conn)
    monkeypatch.setattr(
        "api.node_cleanup.remove_container_user",
        lambda name, username: cleaned.append((name, username)),
    )
    assert delete_account("ada") == ("deleted", 1, 1)
    assert cleaned == [("pool-node-1", "ada")]
    assert conn.committed
    assert any(query.startswith("DELETE FROM users") for query, _params in conn.calls)
    assert "password" not in conn.calls[0][0]


def test_pool_recover_requires_a_session():
    response = TestClient(app).post("/admin/pool/recover")
    assert response.status_code == 401
    assert response.json()["message"] == AUTH_REQUIRED


def test_a_normal_user_cannot_recover_the_pool(monkeypatch):
    client = TestClient(app)
    _login(client, monkeypatch)
    monkeypatch.setattr("api.auth.find_user_role", lambda username: "user")
    response = client.post("/admin/pool/recover")
    assert response.status_code == 403
    assert response.json()["message"] == ADMIN_REQUIRED


def test_admin_recover_reports_how_many_containers_restarted(monkeypatch):
    client = TestClient(app)
    _login(client, monkeypatch, username="admin")
    monkeypatch.setattr("api.auth.find_user_role", lambda username: "admin")
    monkeypatch.setattr("api.main.restart_stopped_pool_containers", lambda: 2)
    response = client.post("/admin/pool/recover")
    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "message": "Pool recovery initiated",
        "restarted": 2,
    }


def test_pool_recover_hides_the_docker_error(monkeypatch):
    from api.errors import PoolRecoverError

    client = TestClient(app)
    _login(client, monkeypatch, username="admin")
    monkeypatch.setattr("api.auth.find_user_role", lambda username: "admin")

    def fail():
        raise PoolRecoverError()

    monkeypatch.setattr("api.main.restart_stopped_pool_containers", fail)
    response = client.post("/admin/pool/recover")
    assert response.status_code == 503
    assert response.json()["message"] == POOL_RECOVER_FAILED
    assert "socket" not in response.text


def test_recover_starts_only_stopped_pool_containers(monkeypatch):
    import docker

    from api.containers import restart_stopped_pool_containers

    started = []

    class Container:
        def __init__(self, name, status):
            self.name = name
            self.status = status

        def start(self):
            started.append(self.name)

    class Client:
        class containers:
            @staticmethod
            def list(all, filters):
                assert all is True
                assert filters == {"name": "pool-node-"}
                return [
                    Container("pool-node-1", "running"),
                    Container("pool-node-2", "exited"),
                    Container("not-pool-node-9", "exited"),
                ]

        def close(self):
            return None

    monkeypatch.setattr(docker, "from_env", lambda: Client())
    assert restart_stopped_pool_containers() == 1
    assert started == ["pool-node-2"]
