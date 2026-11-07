import asyncio
import json
from base64 import b64encode

import itsdangerous

from api.errors import DatabaseUnavailable
from api.settings import get_settings
from api.socket_session import username_from_cookie_header
from api.terminal_socket import TERMINAL_SIGNED_OUT, close_user_terminals, connect


def _signed(payload):
    raw = b64encode(json.dumps(payload).encode("utf-8"))
    signer = itsdangerous.TimestampSigner(get_settings().session_secret)
    return signer.sign(raw).decode("utf-8")


def test_a_signed_session_cookie_yields_the_username():
    cookie = _signed({"username": "ada", "role": "user"})
    assert username_from_cookie_header(f"session={cookie}") == "ada"


def test_a_missing_or_bad_cookie_is_rejected():
    assert username_from_cookie_header(None) is None
    assert username_from_cookie_header("other=1") is None
    assert username_from_cookie_header("session=not-signed") is None
    assert username_from_cookie_header(f"session={_signed({'role': 'user'})}") is None
    assert username_from_cookie_header(f"session={_signed({'username': ''})}") is None


def test_an_expired_cookie_is_rejected(monkeypatch):
    monkeypatch.setattr("api.socket_session.SESSION_MAX_AGE", -1)
    cookie = _signed({"username": "ada"})
    assert username_from_cookie_header(f"session={cookie}") is None


def test_connect_rejects_a_deleted_account(monkeypatch):
    monkeypatch.setattr(
        "api.terminal_socket.username_from_cookie_header",
        lambda header: "ada",
    )
    monkeypatch.setattr("api.terminal_socket.find_user_role", lambda username: None)

    async def run():
        return await connect("sid", {"HTTP_COOKIE": "session=x"})

    assert asyncio.run(run()) is False


def test_connect_rejects_when_the_account_lookup_fails(monkeypatch):
    monkeypatch.setattr(
        "api.terminal_socket.username_from_cookie_header",
        lambda header: "ada",
    )

    def down(username):
        raise DatabaseUnavailable()

    monkeypatch.setattr("api.terminal_socket.find_user_role", down)

    async def run():
        return await connect("sid", {"HTTP_COOKIE": "session=x"})

    assert asyncio.run(run()) is False


def test_connect_rejects_a_socket_without_a_user():
    async def run():
        return await connect("sid", {})

    assert asyncio.run(run()) is False


def test_connect_remembers_the_signed_in_user(monkeypatch):
    saved = {}
    rooms = []

    async def save_session(sid, data):
        saved["sid"] = sid
        saved["data"] = data

    async def enter_room(sid, room):
        rooms.append((sid, room))

    monkeypatch.setattr("api.terminal_socket.sio.save_session", save_session)
    monkeypatch.setattr("api.terminal_socket.sio.enter_room", enter_room)
    monkeypatch.setattr(
        "api.terminal_socket.username_from_cookie_header",
        lambda header: "ada",
    )
    monkeypatch.setattr("api.terminal_socket.find_user_role", lambda username: "user")

    async def run():
        return await connect("sid-1", {"HTTP_COOKIE": "session=ignored"})

    assert asyncio.run(run()) is None
    assert saved == {"sid": "sid-1", "data": {"username": "ada"}}
    assert rooms == [("sid-1", "ada")]


def test_logout_tells_open_terminals_then_disconnects_them(monkeypatch):
    events = []

    class Manager:
        def get_participants(self, namespace, room):
            assert namespace == "/"
            assert room == "ada"
            return [("sid-a", "eio-a")]

    async def emit(event, body, room):
        events.append((event, body, room))

    async def disconnect(sid):
        events.append(("disconnect", sid))

    monkeypatch.setattr("api.terminal_socket.sio.manager", Manager())
    monkeypatch.setattr("api.terminal_socket.sio.emit", emit)
    monkeypatch.setattr("api.terminal_socket.sio.disconnect", disconnect)
    asyncio.run(close_user_terminals("ada"))
    assert events[0] == ("force_disconnect", {"message": TERMINAL_SIGNED_OUT}, "ada")
    assert events[1:] == [("disconnect", "sid-a"), ("disconnect", "sid-a"), ("disconnect", "sid-a")]


def test_two_logouts_sign_the_user_out_once(monkeypatch):
    events = []
    room = [("sid-a", "eio-a")]

    class Manager:
        def get_participants(self, namespace, room_name):
            assert namespace == "/"
            assert room_name == "ada"
            return list(room)

    async def emit(event, body, room):
        events.append((event, body, room))

    async def disconnect(sid):
        events.append(("disconnect", sid))
        del room[:]

    monkeypatch.setattr("api.terminal_socket.sio.manager", Manager())
    monkeypatch.setattr("api.terminal_socket.sio.emit", emit)
    monkeypatch.setattr("api.terminal_socket.sio.disconnect", disconnect)

    async def both():
        await asyncio.gather(close_user_terminals("ada"), close_user_terminals("ada"))

    asyncio.run(both())
    signed_out = [event for event in events if event[0] == "force_disconnect"]
    assert signed_out == [("force_disconnect", {"message": TERMINAL_SIGNED_OUT}, "ada")]
