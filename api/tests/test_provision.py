from fastapi.testclient import TestClient

from api.ansible_jobs import schedule_package_install
from api.errors import ContainerConfigError, DatabaseUnavailable, NotEnoughNodes
from api.main import app
from api.responses import (
    ADMIN_CANNOT_RESERVE,
    AUTH_REQUIRED,
    BAD_PROVISION,
    CONTAINER_CONFIG_FAILED,
    ENCRYPTION_UNAVAILABLE,
    MACHINE_PASSWORD_REJECTED,
    PACKAGE_REJECTED,
    USERNAME_NOT_PROVISIONABLE,
)


def _login(client: TestClient, monkeypatch, role: str = "user") -> None:
    monkeypatch.setattr("api.main.ensure_default_admin", lambda: None)
    monkeypatch.setattr(
        "api.main.authenticate",
        lambda username, password: {"username": "ada", "role": role},
    )
    client.post("/login", json={"username": "ada", "password": "secret"})


def _known_user(monkeypatch, role: str | None = "user") -> None:
    monkeypatch.setattr("api.provisioning.find_user_role", lambda username: role)


def _patch_provision(monkeypatch, nodes, scheduled):
    _known_user(monkeypatch)
    monkeypatch.setattr("api.provisioning.take_free_nodes", lambda count, username, expiry: nodes)
    monkeypatch.setattr(
        "api.provisioning.configure_container", lambda name, username, password: None
    )

    def insert(**kwargs):
        scheduled["cipher"] = kwargs["encrypted_password"]
        return "res-1"

    monkeypatch.setattr("api.provisioning.insert_reservation", insert)
    monkeypatch.setattr(
        "api.provisioning.schedule_package_install",
        lambda username, nodes, password, packages, reservation_id: scheduled.setdefault(
            "packages", packages
        ),
    )


def test_provision_requires_a_session():
    response = TestClient(app).post(
        "/provision",
        json={"vm_count": 1, "duration": 30, "password": "secret"},
    )
    assert response.status_code == 401
    assert response.json()["message"] == AUTH_REQUIRED


def test_admin_cannot_provision(monkeypatch):
    client = TestClient(app)
    _login(client, monkeypatch, role="admin")
    called = {"n": 0}
    monkeypatch.setattr(
        "api.provisioning.take_free_nodes",
        lambda *args: called.__setitem__("n", 1),
    )
    response = client.post(
        "/provision",
        json={"vm_count": 1, "duration": 30, "password": "secret"},
    )
    assert response.status_code == 403
    assert response.json()["message"] == ADMIN_CANNOT_RESERVE
    assert called["n"] == 0


def test_provision_encrypts_the_password_and_starts_ansible(monkeypatch):
    client = TestClient(app)
    _login(client, monkeypatch)
    scheduled = {}
    nodes = [{"name": "pool-node-1", "ip": "172.30.0.2", "port": 3000}]
    _patch_provision(monkeypatch, nodes, scheduled)
    response = client.post(
        "/provision",
        json={"vm_count": 1, "duration": 30, "password": "secret", "packages": "htop, vim"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["reservation_id"] == "res-1"
    assert body["nodes"] == nodes
    assert "secret" not in response.text
    assert scheduled["cipher"] != "secret"
    assert scheduled["packages"] == ["htop", "vim"]


def test_provision_without_packages_passes_an_empty_list(monkeypatch):
    client = TestClient(app)
    _login(client, monkeypatch)
    scheduled = {}
    nodes = [{"name": "pool-node-1", "ip": "172.30.0.2", "port": 3000}]
    _patch_provision(monkeypatch, nodes, scheduled)
    response = client.post(
        "/provision",
        json={"vm_count": 1, "duration": 30, "password": "secret"},
    )
    assert response.status_code == 200
    assert scheduled["packages"] == []


def test_empty_package_list_does_not_start_a_thread(monkeypatch):
    started = {"n": 0}

    class FakeThread:
        def __init__(self, *args, **kwargs):
            started["n"] += 1

        def start(self):
            pass

    monkeypatch.setattr("api.ansible_jobs.threading.Thread", FakeThread)
    schedule_package_install("ada", [], "secret", [], "res-1")
    assert started["n"] == 0


def test_a_failed_thread_start_does_not_fail_the_reservation(monkeypatch):
    class FakeThread:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            raise RuntimeError("can't start new thread")

    monkeypatch.setattr("api.ansible_jobs.threading.Thread", FakeThread)
    schedule_package_install("ada", [{"name": "n"}], "secret", ["htop"], "res-1")


def test_bad_counts_do_not_touch_the_pool(monkeypatch):
    client = TestClient(app)
    _login(client, monkeypatch)
    called = {"n": 0}
    monkeypatch.setattr(
        "api.provisioning.take_free_nodes",
        lambda *args: called.__setitem__("n", 1),
    )
    response = client.post(
        "/provision",
        json={"vm_count": 0, "duration": 30, "password": "secret"},
    )
    assert response.status_code == 400
    assert response.json()["message"] == BAD_PROVISION
    assert called["n"] == 0


def test_container_failure_frees_every_taken_node(monkeypatch):
    client = TestClient(app)
    _login(client, monkeypatch)
    _known_user(monkeypatch)
    freed = {}
    nodes = [{"name": "pool-node-1", "ip": "172.30.0.2", "port": 3000}]
    monkeypatch.setattr(
        "api.provisioning.take_free_nodes",
        lambda count, username, expiry: nodes,
    )
    removed = {}
    monkeypatch.setattr(
        "api.node_cleanup.remove_container_user",
        lambda name, username: removed.setdefault("names", []).append(name),
    )

    def fail(name, username, password):
        raise ContainerConfigError(name)

    monkeypatch.setattr("api.provisioning.configure_container", fail)
    monkeypatch.setattr(
        "api.node_cleanup.free_nodes",
        lambda names, owner: freed.setdefault("names", names),
    )
    response = client.post(
        "/provision",
        json={"vm_count": 1, "duration": 30, "password": "secret"},
    )
    assert response.status_code == 503
    assert response.json()["message"] == CONTAINER_CONFIG_FAILED
    assert freed["names"] == ["pool-node-1"]
    assert removed["names"] == ["pool-node-1"]


def test_rollback_failure_keeps_the_container_error(monkeypatch):
    client = TestClient(app)
    _login(client, monkeypatch)
    _known_user(monkeypatch)
    monkeypatch.setattr(
        "api.provisioning.take_free_nodes",
        lambda count, username, expiry: [{"name": "pool-node-1", "ip": "172.30.0.2", "port": 3000}],
    )
    monkeypatch.setattr("api.node_cleanup.remove_container_user", lambda name, username: None)

    def fail(name, username, password):
        raise ContainerConfigError(name)

    def cannot_free(names, owner):
        raise DatabaseUnavailable()

    monkeypatch.setattr("api.provisioning.configure_container", fail)
    monkeypatch.setattr("api.node_cleanup.free_nodes", cannot_free)
    response = client.post(
        "/provision",
        json={"vm_count": 1, "duration": 30, "password": "secret"},
    )
    assert response.status_code == 503
    assert response.json()["message"] == CONTAINER_CONFIG_FAILED


def test_provision_when_the_pool_is_short(monkeypatch):
    client = TestClient(app)
    _login(client, monkeypatch)
    _known_user(monkeypatch)

    def short(count, username, expiry):
        raise NotEnoughNodes(count, 1)

    monkeypatch.setattr("api.provisioning.take_free_nodes", short)
    response = client.post(
        "/provision",
        json={"vm_count": 2, "duration": 30, "password": "secret"},
    )
    assert response.status_code == 409
    assert response.json()["message"] == (
        "Not enough containers available. You need 2 but only 1 are free."
    )


def test_line_break_or_overlong_password_does_not_touch_the_pool(monkeypatch):
    client = TestClient(app)
    _login(client, monkeypatch)
    called = {"n": 0}
    monkeypatch.setattr(
        "api.provisioning.take_free_nodes",
        lambda *args: called.__setitem__("n", 1),
    )
    broken = client.post(
        "/provision",
        json={"vm_count": 1, "duration": 30, "password": "one\ntwo"},
    )
    too_long = client.post(
        "/provision",
        json={"vm_count": 1, "duration": 30, "password": "a" * 128},
    )
    assert broken.status_code == 400
    assert too_long.status_code == 400
    assert broken.json()["message"] == MACHINE_PASSWORD_REJECTED
    assert too_long.json()["message"] == MACHINE_PASSWORD_REJECTED
    assert called["n"] == 0


def test_password_at_the_column_limit_is_stored(monkeypatch):
    client = TestClient(app)
    _login(client, monkeypatch)
    scheduled = {}
    nodes = [{"name": "pool-node-1", "ip": "172.30.0.2", "port": 3000}]
    _patch_provision(monkeypatch, nodes, scheduled)
    response = client.post(
        "/provision",
        json={"vm_count": 1, "duration": 30, "password": "a" * 127},
    )
    assert response.status_code == 200
    assert len(scheduled["cipher"]) <= 255
    assert "a" * 127 not in response.text


def test_unsafe_username_or_package_does_not_touch_the_pool(monkeypatch):
    called = {"n": 0}
    monkeypatch.setattr(
        "api.provisioning.take_free_nodes",
        lambda *args: called.__setitem__("n", 1),
    )
    monkeypatch.setattr("api.main.ensure_default_admin", lambda: None)
    monkeypatch.setattr(
        "api.main.authenticate",
        lambda username, password: {"username": "9bad", "role": "user"},
    )
    client = TestClient(app)
    client.post("/login", json={"username": "9bad", "password": "secret"})
    unsafe_name = client.post(
        "/provision",
        json={"vm_count": 1, "duration": 30, "password": "secret"},
    )
    assert unsafe_name.status_code == 400
    assert unsafe_name.json()["message"] == USERNAME_NOT_PROVISIONABLE

    client = TestClient(app)
    _login(client, monkeypatch)
    unsafe_package = client.post(
        "/provision",
        json={"vm_count": 1, "duration": 30, "password": "secret", "packages": "htop, Bad"},
    )
    assert unsafe_package.status_code == 400
    assert unsafe_package.json()["message"] == PACKAGE_REJECTED
    assert called["n"] == 0


def test_database_role_blocks_a_stale_user_cookie(monkeypatch):
    client = TestClient(app)
    _login(client, monkeypatch)
    _known_user(monkeypatch, role="admin")
    called = {"n": 0}
    monkeypatch.setattr(
        "api.provisioning.take_free_nodes",
        lambda *args: called.__setitem__("n", 1),
    )
    response = client.post(
        "/provision",
        json={"vm_count": 1, "duration": 30, "password": "secret"},
    )
    assert response.status_code == 403
    assert response.json()["message"] == ADMIN_CANNOT_RESERVE
    assert called["n"] == 0


def test_missing_account_does_not_touch_the_pool(monkeypatch):
    client = TestClient(app)
    _login(client, monkeypatch)
    _known_user(monkeypatch, role=None)
    called = {"n": 0}
    monkeypatch.setattr(
        "api.provisioning.take_free_nodes",
        lambda *args: called.__setitem__("n", 1),
    )
    response = client.post(
        "/provision",
        json={"vm_count": 1, "duration": 30, "password": "secret"},
    )
    assert response.status_code == 401
    assert response.json()["message"] == AUTH_REQUIRED
    assert called["n"] == 0


def test_encryption_failure_does_not_touch_the_pool(monkeypatch):
    client = TestClient(app)
    _login(client, monkeypatch)
    called = {"n": 0}
    monkeypatch.setattr(
        "api.provisioning.take_free_nodes",
        lambda *args: called.__setitem__("n", 1),
    )

    def broken(password):
        raise ValueError("bad key")

    monkeypatch.setattr("api.provisioning.encrypt_machine_password", broken)
    response = client.post(
        "/provision",
        json={"vm_count": 1, "duration": 30, "password": "secret"},
    )
    assert response.status_code == 503
    assert response.json()["message"] == ENCRYPTION_UNAVAILABLE
    assert "bad key" not in response.text
    assert called["n"] == 0


def test_configure_passes_the_password_outside_the_shell(monkeypatch):
    import docker

    from api.containers import configure_container

    calls = []

    class Result:
        def __init__(self, code):
            self.exit_code = code

    class Container:
        def exec_run(self, cmd):
            calls.append(cmd)
            if cmd[0] == "id":
                return Result(1)
            return Result(0)

    class Containers:
        def get(self, name):
            return Container()

    class Client:
        containers = Containers()

        def close(self):
            calls.append("closed")

    monkeypatch.setattr(docker, "from_env", lambda: Client())
    configure_container("pool-node-1", "ada", "s ecret")
    assert calls[0] == ["id", "-u", "--", "ada"]
    assert calls[1] == ["useradd", "-m", "-s", "/bin/bash", "--", "ada"]
    assert calls[2][0] == "sh"
    assert "s ecret" not in " ".join(str(part) for part in calls[2])
    assert calls[3] == ["usermod", "-aG", "sudo", "--", "ada"]
    assert calls[4] == "closed"


def test_docker_socket_failure_is_a_container_error(monkeypatch):
    import docker
    import pytest

    from api.containers import configure_container
    from api.errors import ContainerConfigError

    def fail():
        raise docker.errors.DockerException("socket down")

    monkeypatch.setattr(docker, "from_env", fail)
    with pytest.raises(ContainerConfigError):
        configure_container("pool-node-1", "ada", "secret")


def test_exec_failure_is_a_container_error(monkeypatch):
    import docker
    import pytest

    from api.containers import configure_container
    from api.errors import ContainerConfigError

    closed = {"n": 0}

    class Container:
        def exec_run(self, cmd):
            raise docker.errors.DockerException("exec failed")

    class Client:
        containers = type("Containers", (), {"get": lambda self, name: Container()})()

        def close(self):
            closed["n"] += 1

    monkeypatch.setattr(docker, "from_env", lambda: Client())
    with pytest.raises(ContainerConfigError):
        configure_container("pool-node-1", "ada", "secret")
    assert closed["n"] == 1


def test_closing_the_docker_client_cannot_hide_success(monkeypatch):
    import docker

    from api.containers import configure_container

    class Result:
        exit_code = 0

    class Container:
        def exec_run(self, cmd):
            return Result()

    class Client:
        containers = type("Containers", (), {"get": lambda self, name: Container()})()

        def close(self):
            raise docker.errors.DockerException("close failed")

    monkeypatch.setattr(docker, "from_env", lambda: Client())
    configure_container("pool-node-1", "ada", "secret")


def test_database_close_after_commit_keeps_the_reservation(monkeypatch):
    import psycopg

    from api.reservation_sql import insert_reservation

    class Conn:
        def __init__(self):
            self.committed = False

        def execute(self, query, params=None):
            return self

        def fetchone(self):
            return {"id": 7}

        def commit(self):
            self.committed = True

        def rollback(self):
            raise AssertionError("should not roll back")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            if self.committed:
                raise psycopg.OperationalError("connection closed")
            return False

    monkeypatch.setattr("api.reservation_sql.connect", lambda: Conn())
    reservation_id = insert_reservation(
        username="ada",
        vm_count=1,
        duration_minutes=60,
        expires_at=1,
        nodes=[{"name": "n1", "ip": "172.30.0.2", "port": 3001}],
        packages=["htop"],
        encrypted_password="token",
    )
    assert reservation_id


def test_sudo_failure_aborts_configuration(monkeypatch):
    import docker
    import pytest

    from api.containers import configure_container
    from api.errors import ContainerConfigError

    class Result:
        def __init__(self, code):
            self.exit_code = code

    class Container:
        def exec_run(self, cmd):
            if cmd[0] == "id":
                return Result(1)
            if cmd[0] == "usermod":
                return Result(6)
            return Result(0)

    class Client:
        containers = type("Containers", (), {"get": lambda self, name: Container()})()

        def close(self):
            return None

    monkeypatch.setattr(docker, "from_env", lambda: Client())
    with pytest.raises(ContainerConfigError):
        configure_container("pool-node-1", "ada", "secret")


def test_reserved_username_does_not_touch_the_pool(monkeypatch):
    monkeypatch.setattr("api.main.ensure_default_admin", lambda: None)
    monkeypatch.setattr(
        "api.main.authenticate",
        lambda username, password: {"username": "root", "role": "user"},
    )
    client = TestClient(app)
    client.post("/login", json={"username": "root", "password": "secret"})
    _known_user(monkeypatch)
    called = {"n": 0}
    monkeypatch.setattr(
        "api.provisioning.take_free_nodes",
        lambda *args: called.__setitem__("n", 1),
    )
    response = client.post(
        "/provision",
        json={"vm_count": 1, "duration": 30, "password": "secret"},
    )
    assert response.status_code == 400
    assert response.json()["message"] == USERNAME_NOT_PROVISIONABLE
    assert called["n"] == 0


def test_inventory_quotes_the_password_and_is_private(tmp_path, monkeypatch):
    import subprocess

    from api.ansible_jobs import _install

    monkeypatch.setattr("api.ansible_jobs.INVENTORY_DIR", tmp_path)
    monkeypatch.setattr("api.ansible_jobs.PLAYBOOK", tmp_path / "playbook.yml")
    inventory = tmp_path / "inventory_res-1.yml"
    captured = {}

    def fake_run(*args, **kwargs):
        captured["text"] = inventory.read_text(encoding="utf-8")
        captured["mode"] = inventory.stat().st_mode & 0o777

    monkeypatch.setattr(subprocess, "run", fake_run)
    _install(
        "ada",
        [{"name": "pool-node-1", "ip": "172.30.0.2", "port": 3000}],
        'sek ret#1"',
        ["htop"],
        "res-1",
    )
    assert not inventory.exists()
    text = captured["text"]
    assert 'ansible_ssh_pass: "sek ret#1\\""' in text
    assert "sek ret#1" not in text.replace('"sek ret#1\\""', "")
    assert captured["mode"] == 0o600


def test_inventory_id_cannot_escape_the_directory(tmp_path, monkeypatch):
    import subprocess

    from api.ansible_jobs import _install

    monkeypatch.setattr("api.ansible_jobs.INVENTORY_DIR", tmp_path)
    monkeypatch.setattr("api.ansible_jobs.PLAYBOOK", tmp_path / "playbook.yml")
    called = {"n": 0}
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: called.__setitem__("n", 1),
    )
    _install(
        "ada",
        [{"name": "pool-node-1", "ip": "172.30.0.2", "port": 3000}],
        "secret",
        ["htop"],
        "../outside",
    )
    assert called["n"] == 0
    assert list(tmp_path.iterdir()) == []
    assert not (tmp_path.parent / "outside.yml").exists()


def test_inventory_quotes_names_ansible_would_read_as_booleans():
    from api.ansible_jobs import _inventory_yaml

    text = _inventory_yaml(
        "on",
        [{"name": "yes", "ip": "172.30.0.2", "port": 3000}],
        "secret",
        ["htop"],
    )
    assert text.startswith('"on":\n')
    assert '    "yes":\n' in text
    assert 'ansible_user: "on"' in text


def test_taking_nodes_survives_a_database_close_after_commit(monkeypatch):
    import psycopg

    from api.pool_sql import free_nodes, take_free_nodes

    class Conn:
        def __init__(self):
            self.committed = False

        def execute(self, query, params=None):
            return self

        def fetchall(self):
            return [{"name": "pool-node-1", "ip": "172.30.0.2", "port": 3000}]

        def commit(self):
            self.committed = True

        def rollback(self):
            raise AssertionError("should not roll back")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            if self.committed:
                raise psycopg.OperationalError("connection closed")
            return False

    monkeypatch.setattr("api.pool_sql.connect", lambda: Conn())
    nodes = take_free_nodes(1, "ada", 100)
    assert nodes == [{"name": "pool-node-1", "ip": "172.30.0.2", "port": 3000}]
    free_nodes(["pool-node-1"], "ada")


def test_a_short_pool_stays_not_enough_when_the_connection_closes(monkeypatch):
    import psycopg

    from api.pool_sql import take_free_nodes
    from api.reservation_sql import insert_reservation

    class Conn:
        def execute(self, query, params=None):
            return self

        def fetchall(self):
            return []

        def fetchone(self):
            return None

        def rollback(self):
            return None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            raise psycopg.OperationalError("connection closed")

    monkeypatch.setattr("api.pool_sql.connect", lambda: Conn())
    try:
        take_free_nodes(1, "ada", 100)
    except NotEnoughNodes as exc:
        assert (exc.requested, exc.free) == (1, 0)
    else:
        raise AssertionError("expected NotEnoughNodes")

    monkeypatch.setattr("api.reservation_sql.connect", lambda: Conn())
    assert (
        insert_reservation(
            username="missing",
            vm_count=1,
            duration_minutes=60,
            expires_at=1,
            nodes=[],
            packages=[],
            encrypted_password="token",
        )
        is None
    )
