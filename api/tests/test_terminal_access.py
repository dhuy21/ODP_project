import asyncio

from api.errors import DatabaseUnavailable
from api.reservation_sql import find_active_terminal_reservation
from api.responses import DATABASE_UNAVAILABLE
from api.terminal_access import (
    TERMINAL_NO_RESERVATION,
    TERMINAL_NODE_REQUIRED,
    TERMINAL_UNAUTHORIZED,
    reservation_info,
)
from api.terminal_socket import request_reservation_info


def test_the_lookup_does_not_select_the_machine_password(monkeypatch):
    seen = {}

    def fetch_all(query, params=None):
        seen["query"] = query
        return [{"id": "res-1"}]

    monkeypatch.setattr("api.reservation_sql.fetch_all", fetch_all)
    assert find_active_terminal_reservation("ada", "pool-node-1", 10) == "res-1"
    assert "vm_password" not in seen["query"]


def test_someone_else_cannot_ask_for_a_terminal():
    body = reservation_info("ada", "grace", "pool-node-1", 10)
    assert body == {"error": TERMINAL_UNAUTHORIZED}
    assert "password" not in body


def test_a_missing_node_name_is_rejected(monkeypatch):
    monkeypatch.setattr(
        "api.terminal_access.find_active_terminal_reservation",
        lambda username, node_name, now: "res-1",
    )
    assert reservation_info("ada", "ada", "", 10) == {"error": TERMINAL_NODE_REQUIRED}
    assert reservation_info("ada", "ada", None, 10) == {"error": TERMINAL_NODE_REQUIRED}


def test_an_inactive_node_is_rejected(monkeypatch):
    monkeypatch.setattr(
        "api.terminal_access.find_active_terminal_reservation",
        lambda username, node_name, now: None,
    )
    body = reservation_info("ada", "ada", "pool-node-1", 10)
    assert body == {"error": TERMINAL_NO_RESERVATION}
    assert "password" not in body


def test_an_active_node_is_described_without_a_password(monkeypatch):
    monkeypatch.setattr(
        "api.terminal_access.find_active_terminal_reservation",
        lambda username, node_name, now: "res-1",
    )
    body = reservation_info("ada", "ada", "pool-node-1", 10)
    assert body == {
        "reservation_id": "res-1",
        "username": "ada",
        "node_name": "pool-node-1",
    }
    assert "password" not in body


def test_the_socket_event_hides_a_database_failure(monkeypatch):
    sent = {}

    async def get_session(sid):
        return {"username": "ada"}

    async def emit(event, body, to):
        sent["event"] = event
        sent["body"] = body
        sent["to"] = to

    def down(socket_username, requested_username, node_name, now):
        raise DatabaseUnavailable()

    monkeypatch.setattr("api.terminal_socket.sio.get_session", get_session)
    monkeypatch.setattr("api.terminal_socket.sio.emit", emit)
    monkeypatch.setattr("api.terminal_socket.reservation_info", down)

    asyncio.run(request_reservation_info("sid-1", {"username": "ada", "node_name": "n"}))
    assert sent == {
        "event": "reservation_info",
        "body": {"error": DATABASE_UNAVAILABLE},
        "to": "sid-1",
    }
    assert "password" not in sent["body"]
