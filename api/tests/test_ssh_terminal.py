import asyncio
import threading
import time

from api.machine_passwords import decrypt_machine_password, encrypt_machine_password
from api.ssh_terminal import (
    OPEN_CANCELLED,
    TERMINAL_OPEN_FAILED,
    close_terminal,
    open_terminal,
    resize_terminal,
    send_input,
    start_output,
)
from api.terminal_socket import connect_ssh, terminal_input
from api.terminal_access import TERMINAL_NO_RESERVATION, TERMINAL_UNAUTHORIZED


class _Client:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


def test_decrypt_matches_encrypt():
    token = encrypt_machine_password("machine-secret")
    assert decrypt_machine_password(token) == "machine-secret"


def test_ssh_uses_the_database_password_not_the_browser_one(monkeypatch):
    seen = {}

    def endpoint(username, node_name, now):
        return "res-1", 3000, "token"

    def client(username, port, password):
        seen["username"] = username
        seen["port"] = port
        seen["password"] = password
        return _Client()

    monkeypatch.setattr(
        "api.ssh_terminal.reservation_info",
        lambda socket_username, requested, node_name, now: {
            "reservation_id": "res-1",
            "username": socket_username,
            "node_name": node_name,
        },
    )
    monkeypatch.setattr("api.ssh_terminal.load_terminal_endpoint", endpoint)
    monkeypatch.setattr("api.ssh_terminal.decrypt_machine_password", lambda token: "secret-db")
    monkeypatch.setattr("api.ssh_terminal._ssh_client", client)

    assert open_terminal("ada", "ada", "pool-node-1", 10, "sid-1") is None
    assert seen == {"username": "ada", "port": 3000, "password": "secret-db"}
    close_terminal("sid-1")


class _Channel:
    def __init__(self, chunks):
        self.chunks = list(chunks)
        self.closed = False

    def recv_ready(self):
        return bool(self.chunks)

    def recv(self, size):
        if not self.chunks:
            self.closed = True
            return b""
        return self.chunks.pop(0)


def test_shell_output_is_forwarded_until_the_channel_closes(monkeypatch):
    sent = []
    channel = _Channel([b"hello"])

    class Client(_Client):
        def __init__(self):
            super().__init__()
            self.channel = channel

    monkeypatch.setattr(
        "api.ssh_terminal.reservation_info",
        lambda socket_username, requested, node_name, now: {
            "reservation_id": "res-1",
            "username": socket_username,
            "node_name": node_name,
        },
    )
    monkeypatch.setattr(
        "api.ssh_terminal.load_terminal_endpoint",
        lambda username, node_name, now: ("res-1", 3000, "token"),
    )
    monkeypatch.setattr("api.ssh_terminal.decrypt_machine_password", lambda token: "secret-db")
    monkeypatch.setattr("api.ssh_terminal._ssh_client", lambda username, port, password: Client())

    assert open_terminal("ada", "ada", "pool-node-1", 10, "sid-out") is None

    def emit(text):
        sent.append(text)
        channel.closed = True

    start_output("sid-out", emit)
    for _ in range(50):
        if sent:
            break
        time.sleep(0.01)
    close_terminal("sid-out")
    assert sent == ["hello"]


def _open_fake_shell(monkeypatch, sid, channel):
    class Client(_Client):
        def __init__(self):
            super().__init__()
            self.channel = channel

    monkeypatch.setattr(
        "api.ssh_terminal.reservation_info",
        lambda socket_username, requested, node_name, now: {
            "reservation_id": "res-1",
            "username": socket_username,
            "node_name": node_name,
        },
    )
    monkeypatch.setattr(
        "api.ssh_terminal.load_terminal_endpoint",
        lambda username, node_name, now: ("res-1", 3000, "token"),
    )
    monkeypatch.setattr("api.ssh_terminal.decrypt_machine_password", lambda token: "secret-db")
    monkeypatch.setattr("api.ssh_terminal._ssh_client", lambda username, port, password: Client())
    assert open_terminal("ada", "ada", "pool-node-1", 10, sid) is None


def test_opening_applies_the_initial_terminal_size(monkeypatch):
    seen = {}
    channel = _Channel([])

    def resize_pty(width, height):
        seen["width"] = width
        seen["height"] = height

    channel.resize_pty = resize_pty

    class Client(_Client):
        def __init__(self):
            super().__init__()
            self.channel = channel

    monkeypatch.setattr(
        "api.ssh_terminal.reservation_info",
        lambda socket_username, requested, node_name, now: {
            "reservation_id": "res-1",
            "username": socket_username,
            "node_name": node_name,
        },
    )
    monkeypatch.setattr(
        "api.ssh_terminal.load_terminal_endpoint",
        lambda username, node_name, now: ("res-1", 3000, "token"),
    )
    monkeypatch.setattr("api.ssh_terminal.decrypt_machine_password", lambda token: "secret-db")
    monkeypatch.setattr("api.ssh_terminal._ssh_client", lambda username, port, password: Client())
    assert open_terminal("ada", "ada", "pool-node-1", 10, "sid-fit", 100, 30) is None
    close_terminal("sid-fit")
    assert seen == {"width": 100, "height": 30}


def test_an_expired_shell_is_closed(monkeypatch):
    noticed = []
    channel = _Channel([])

    class Client(_Client):
        def __init__(self):
            super().__init__()
            self.channel = channel
            self.expires_at = 1

    held = {}

    def client(username, port, password):
        held["client"] = Client()
        return held["client"]

    monkeypatch.setattr(
        "api.ssh_terminal.reservation_info",
        lambda socket_username, requested, node_name, now: {
            "reservation_id": "res-1",
            "username": socket_username,
            "node_name": node_name,
        },
    )
    monkeypatch.setattr(
        "api.ssh_terminal.load_terminal_endpoint",
        lambda username, node_name, now: ("res-1", 3000, "token", 1),
    )
    monkeypatch.setattr("api.ssh_terminal.decrypt_machine_password", lambda token: "secret-db")
    monkeypatch.setattr("api.ssh_terminal._ssh_client", client)
    assert open_terminal("ada", "ada", "pool-node-1", 10, "sid-exp") is None
    start_output("sid-exp", lambda text: None, lambda: noticed.append("Reservation expired"))
    for _ in range(50):
        if noticed and held["client"].closed:
            break
        time.sleep(0.01)
    assert noticed == ["Reservation expired"]
    assert held["client"].closed is True
    assert send_input("sid-exp", "a") is None
    close_terminal("sid-exp")


def test_a_channel_that_closes_after_the_deadline_says_expired(monkeypatch):
    noticed = []
    channel = _Channel([b"x"])
    held = {}

    class Client(_Client):
        def __init__(self):
            super().__init__()
            self.channel = channel
            self.expires_at = time.time() + 3600

    def recv(size):
        held["client"].expires_at = 1
        return b""

    channel.recv = recv

    def client(username, port, password):
        held["client"] = Client()
        return held["client"]

    monkeypatch.setattr(
        "api.ssh_terminal.reservation_info",
        lambda socket_username, requested, node_name, now: {
            "reservation_id": "res-1",
            "username": socket_username,
            "node_name": node_name,
        },
    )
    monkeypatch.setattr(
        "api.ssh_terminal.load_terminal_endpoint",
        lambda username, node_name, now: ("res-1", 3000, "token", time.time() + 3600),
    )
    monkeypatch.setattr("api.ssh_terminal.decrypt_machine_password", lambda token: "secret-db")
    monkeypatch.setattr("api.ssh_terminal._ssh_client", client)
    assert open_terminal("ada", "ada", "pool-node-1", 10, "sid-late") is None
    start_output("sid-late", lambda text: None, lambda: noticed.append("Reservation expired"))
    for _ in range(50):
        if noticed and held["client"].closed:
            break
        time.sleep(0.01)
    assert noticed == ["Reservation expired"]
    assert held["client"].closed is True
    assert send_input("sid-late", "a") is None
    close_terminal("sid-late")


def test_an_exit_before_the_deadline_is_not_reported_as_expired(monkeypatch):
    noticed = []
    channel = _Channel([b""])
    held = {}

    class Client(_Client):
        def __init__(self):
            super().__init__()
            self.channel = channel
            self.expires_at = time.time() + 3600

    def client(username, port, password):
        held["client"] = Client()
        return held["client"]

    monkeypatch.setattr(
        "api.ssh_terminal.reservation_info",
        lambda socket_username, requested, node_name, now: {
            "reservation_id": "res-1",
            "username": socket_username,
            "node_name": node_name,
        },
    )
    monkeypatch.setattr(
        "api.ssh_terminal.load_terminal_endpoint",
        lambda username, node_name, now: ("res-1", 3000, "token", time.time() + 3600),
    )
    monkeypatch.setattr("api.ssh_terminal.decrypt_machine_password", lambda token: "secret-db")
    monkeypatch.setattr("api.ssh_terminal._ssh_client", client)
    assert open_terminal("ada", "ada", "pool-node-1", 10, "sid-exit") is None
    start_output("sid-exit", lambda text: None, lambda: noticed.append("Reservation expired"))
    for _ in range(50):
        if held["client"].closed:
            break
        time.sleep(0.01)
    assert held["client"].closed is True
    assert noticed == []
    assert send_input("sid-exit", "a") is False
    close_terminal("sid-exit")


def test_an_expired_shell_closes_when_the_notice_fails(monkeypatch):
    channel = _Channel([])

    class Client(_Client):
        def __init__(self):
            super().__init__()
            self.channel = channel
            self.expires_at = 1

    held = {}

    def client(username, port, password):
        held["client"] = Client()
        return held["client"]

    def fail():
        raise RuntimeError("loop closed")

    monkeypatch.setattr(
        "api.ssh_terminal.reservation_info",
        lambda socket_username, requested, node_name, now: {
            "reservation_id": "res-1",
            "username": socket_username,
            "node_name": node_name,
        },
    )
    monkeypatch.setattr(
        "api.ssh_terminal.load_terminal_endpoint",
        lambda username, node_name, now: ("res-1", 3000, "token", 1),
    )
    monkeypatch.setattr("api.ssh_terminal.decrypt_machine_password", lambda token: "secret-db")
    monkeypatch.setattr("api.ssh_terminal._ssh_client", client)
    assert open_terminal("ada", "ada", "pool-node-1", 10, "sid-exp-fail") is None
    start_output("sid-exp-fail", lambda text: None, fail)
    for _ in range(50):
        if held["client"].closed:
            break
        time.sleep(0.01)
    assert held["client"].closed is True
    assert send_input("sid-exp-fail", "a") is False
    close_terminal("sid-exp-fail")


def test_resize_reaches_only_the_open_shell(monkeypatch):
    seen = {}
    channel = _Channel([])

    def resize_pty(width, height):
        seen["width"] = width
        seen["height"] = height

    channel.resize_pty = resize_pty
    _open_fake_shell(monkeypatch, "sid-size", channel)
    resize_terminal("sid-size", 120, 40)
    resize_terminal("sid-size", True, 40)
    resize_terminal("sid-size", 0, 40)
    resize_terminal("sid-size", 1200, 40)
    resize_terminal("missing", 80, 24)
    close_terminal("sid-size")
    assert seen == {"width": 120, "height": 40}


def test_keystrokes_go_to_the_open_shell(monkeypatch):
    sent = []
    channel = _Channel([])

    def send(data):
        sent.append(data)
        return len(data)

    channel.send = send
    _open_fake_shell(monkeypatch, "sid-in", channel)
    assert send_input("sid-in", "ls\n") is True
    close_terminal("sid-in")
    assert send_input("sid-in", "ls\n") is None
    assert sent == [b"ls\n"]


def test_two_keystrokes_are_not_sent_at_once(monkeypatch):
    state = {"inside": 0, "max": 0}
    channel = _Channel([])

    def send(data):
        state["inside"] += 1
        state["max"] = max(state["max"], state["inside"])
        time.sleep(0.05)
        state["inside"] -= 1
        return len(data)

    channel.send = send
    _open_fake_shell(monkeypatch, "sid-par", channel)
    threads = [
        threading.Thread(target=send_input, args=("sid-par", "a")),
        threading.Thread(target=send_input, args=("sid-par", "b")),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    close_terminal("sid-par")
    assert state["max"] == 1
    assert send_input("sid-par", "c") is None


def test_a_failed_second_open_keeps_the_working_shell(monkeypatch):
    channel = _Channel([])
    sent = []

    def send(data):
        sent.append(data)
        return len(data)

    channel.send = send
    calls = {"n": 0}

    def endpoint(username, node_name, now):
        calls["n"] += 1
        if calls["n"] == 1:
            return "res-1", 3000, "token"
        return None

    class Client(_Client):
        def __init__(self):
            super().__init__()
            self.channel = channel

    monkeypatch.setattr(
        "api.ssh_terminal.reservation_info",
        lambda socket_username, requested, node_name, now: {
            "reservation_id": "res-1",
            "username": socket_username,
            "node_name": node_name,
        },
    )
    monkeypatch.setattr("api.ssh_terminal.load_terminal_endpoint", endpoint)
    monkeypatch.setattr("api.ssh_terminal.decrypt_machine_password", lambda token: "secret-db")
    monkeypatch.setattr("api.ssh_terminal._ssh_client", lambda username, port, password: Client())
    assert open_terminal("ada", "ada", "pool-node-1", 10, "sid-keep") is None
    assert open_terminal("ada", "ada", "pool-node-1", 10, "sid-keep") == {
        "error": TERMINAL_NO_RESERVATION
    }
    assert send_input("sid-keep", "a") is True
    assert sent == [b"a"]
    close_terminal("sid-keep")
    assert calls["n"] == 2


def test_an_overlapping_open_leaves_the_first_shell(monkeypatch):
    channel = _Channel([])
    sent = []

    def send(data):
        sent.append(data)
        return len(data)

    channel.send = send
    started = threading.Event()
    release = threading.Event()

    def client(username, port, password):
        started.set()
        assert release.wait(2)
        made = _Client()
        made.channel = channel
        return made

    monkeypatch.setattr(
        "api.ssh_terminal.reservation_info",
        lambda socket_username, requested, node_name, now: {
            "reservation_id": "res-1",
            "username": socket_username,
            "node_name": node_name,
        },
    )
    monkeypatch.setattr(
        "api.ssh_terminal.load_terminal_endpoint",
        lambda username, node_name, now: ("res-1", 3000, "token"),
    )
    monkeypatch.setattr("api.ssh_terminal.decrypt_machine_password", lambda token: "secret-db")
    monkeypatch.setattr("api.ssh_terminal._ssh_client", client)
    holder = {}

    def first():
        holder["result"] = open_terminal("ada", "ada", "pool-node-1", 10, "sid-overlap")

    thread = threading.Thread(target=first)
    thread.start()
    assert started.wait(2)
    second = open_terminal("ada", "ada", "pool-node-1", 10, "sid-overlap")
    release.set()
    thread.join(2)
    assert holder["result"] is None
    assert second is OPEN_CANCELLED
    assert send_input("sid-overlap", "a") is True
    assert sent == [b"a"]
    close_terminal("sid-overlap")


def test_a_failed_ssh_retry_keeps_the_working_shell(monkeypatch):
    channel = _Channel([])
    sent = []

    def send(data):
        sent.append(data)
        return len(data)

    channel.send = send
    calls = {"n": 0}

    def client(username, port, password):
        calls["n"] += 1
        if calls["n"] == 1:
            made = _Client()
            made.channel = channel
            return made
        raise OSError("ssh down")

    monkeypatch.setattr(
        "api.ssh_terminal.reservation_info",
        lambda socket_username, requested, node_name, now: {
            "reservation_id": "res-1",
            "username": socket_username,
            "node_name": node_name,
        },
    )
    monkeypatch.setattr(
        "api.ssh_terminal.load_terminal_endpoint",
        lambda username, node_name, now: ("res-1", 3000, "token"),
    )
    monkeypatch.setattr("api.ssh_terminal.decrypt_machine_password", lambda token: "secret-db")
    monkeypatch.setattr("api.ssh_terminal._ssh_client", client)
    assert open_terminal("ada", "ada", "pool-node-1", 10, "sid-retry") is None
    assert open_terminal("ada", "ada", "pool-node-1", 10, "sid-retry") == {
        "error": TERMINAL_OPEN_FAILED
    }
    assert send_input("sid-retry", "a") is True
    assert sent == [b"a"]
    close_terminal("sid-retry")


def test_a_keystroke_while_the_endpoint_loads_is_not_a_failure(monkeypatch):
    seen = {}

    def endpoint(username, node_name, now):
        seen["during"] = send_input("sid-load", "a")
        return "res-1", 3000, "token"

    monkeypatch.setattr(
        "api.ssh_terminal.reservation_info",
        lambda socket_username, requested, node_name, now: {
            "reservation_id": "res-1",
            "username": socket_username,
            "node_name": node_name,
        },
    )
    monkeypatch.setattr("api.ssh_terminal.load_terminal_endpoint", endpoint)
    monkeypatch.setattr("api.ssh_terminal.decrypt_machine_password", lambda token: "secret-db")
    monkeypatch.setattr("api.ssh_terminal._ssh_client", lambda username, port, password: _Client())
    assert open_terminal("ada", "ada", "pool-node-1", 10, "sid-load") is None
    close_terminal("sid-load")
    assert seen["during"] is None


def test_a_keystroke_during_connect_is_not_a_failure(monkeypatch):
    seen = {}

    def client(username, port, password):
        seen["during"] = send_input("sid-wait", "a")
        return _Client()

    monkeypatch.setattr(
        "api.ssh_terminal.reservation_info",
        lambda socket_username, requested, node_name, now: {
            "reservation_id": "res-1",
            "username": socket_username,
            "node_name": node_name,
        },
    )
    monkeypatch.setattr(
        "api.ssh_terminal.load_terminal_endpoint",
        lambda username, node_name, now: ("res-1", 3000, "token"),
    )
    monkeypatch.setattr("api.ssh_terminal.decrypt_machine_password", lambda token: "secret-db")
    monkeypatch.setattr("api.ssh_terminal._ssh_client", client)
    assert open_terminal("ada", "ada", "pool-node-1", 10, "sid-wait") is None
    close_terminal("sid-wait")
    assert seen["during"] is None


def test_a_keystroke_before_any_shell_is_not_an_error(monkeypatch):
    emitted = []

    async def emit(event, body, to):
        emitted.append((event, body, to))

    monkeypatch.setattr("api.terminal_socket.sio.emit", emit)
    asyncio.run(terminal_input("sid-early", {"data": "a"}))
    assert emitted == []
    assert send_input("sid-early", "a") is None


def test_a_keystroke_after_the_shell_ends_is_a_failure(monkeypatch):
    from api import ssh_terminal

    channel = _Channel([b"hello"])
    channel.send = lambda data: len(data)

    class Client(_Client):
        def __init__(self):
            super().__init__()
            self.channel = channel

    monkeypatch.setattr(
        "api.ssh_terminal.reservation_info",
        lambda socket_username, requested, node_name, now: {
            "reservation_id": "res-1",
            "username": socket_username,
            "node_name": node_name,
        },
    )
    monkeypatch.setattr(
        "api.ssh_terminal.load_terminal_endpoint",
        lambda username, node_name, now: ("res-1", 3000, "token"),
    )
    monkeypatch.setattr("api.ssh_terminal.decrypt_machine_password", lambda token: "secret-db")
    monkeypatch.setattr("api.ssh_terminal._ssh_client", lambda username, port, password: Client())
    assert open_terminal("ada", "ada", "pool-node-1", 10, "sid-ended") is None

    def emit(text):
        channel.closed = True

    start_output("sid-ended", emit)
    for _ in range(50):
        if "sid-ended" in ssh_terminal._closed_sids:
            break
        time.sleep(0.01)
    assert send_input("sid-ended", "a") is False
    close_terminal("sid-ended")
    assert send_input("sid-ended", "b") is None


def test_a_reconnect_survives_the_old_shell_failing_to_close(monkeypatch):
    sent = []
    channel = _Channel([])
    channel.send = lambda data: sent.append(data) or len(data)
    calls = {"n": 0}

    def client(username, port, password):
        calls["n"] += 1
        made = _Client()
        if calls["n"] == 1:

            def fail():
                raise OSError("close failed")

            made.close = fail
            return made
        made.channel = channel
        return made

    monkeypatch.setattr(
        "api.ssh_terminal.reservation_info",
        lambda socket_username, requested, node_name, now: {
            "reservation_id": "res-1",
            "username": socket_username,
            "node_name": node_name,
        },
    )
    monkeypatch.setattr(
        "api.ssh_terminal.load_terminal_endpoint",
        lambda username, node_name, now: ("res-1", 3000, "token"),
    )
    monkeypatch.setattr("api.ssh_terminal.decrypt_machine_password", lambda token: "secret-db")
    monkeypatch.setattr("api.ssh_terminal._ssh_client", client)
    assert open_terminal("ada", "ada", "pool-node-1", 10, "sid-re") is None
    assert open_terminal("ada", "ada", "pool-node-1", 10, "sid-re") is None
    assert send_input("sid-re", "a") is True
    assert sent == [b"a"]
    close_terminal("sid-re")


def test_a_keystroke_while_connecting_is_ignored(monkeypatch):
    emitted = []

    async def emit(event, body, to):
        emitted.append((event, body, to))

    monkeypatch.setattr("api.terminal_socket.sio.emit", emit)
    monkeypatch.setattr("api.terminal_socket.send_input", lambda sid, data: None)
    asyncio.run(terminal_input("sid", {"data": "a"}))
    assert emitted == []


def test_a_partial_send_is_finished(monkeypatch):
    pieces = []
    channel = _Channel([])

    def send(data):
        pieces.append(data[:1])
        return 1

    channel.send = send
    _open_fake_shell(monkeypatch, "sid-part", channel)
    assert send_input("sid-part", "ab") is True
    close_terminal("sid-part")
    assert b"".join(pieces) == b"ab"


def test_a_keystroke_in_flight_when_the_shell_ends_is_a_failure(monkeypatch):
    from api import ssh_terminal

    channel = _Channel([])

    def send(data):
        ssh_terminal._close_if_current("sid-end-send", ssh_terminal._sessions["sid-end-send"])
        raise OSError("closed")

    channel.send = send
    _open_fake_shell(monkeypatch, "sid-end-send", channel)
    assert send_input("sid-end-send", "a") is False
    close_terminal("sid-end-send")


def test_a_delivered_key_is_kept_when_the_shell_ends(monkeypatch):
    from api import ssh_terminal

    channel = _Channel([])

    def send(data):
        ssh_terminal._close_if_current("sid-sent", ssh_terminal._sessions["sid-sent"])
        return len(data)

    channel.send = send
    _open_fake_shell(monkeypatch, "sid-sent", channel)
    assert send_input("sid-sent", "a") is True
    close_terminal("sid-sent")


def test_a_send_error_on_a_replaced_shell_is_dropped(monkeypatch):
    channel = _Channel([])

    def send(data):
        close_terminal("sid-swap")
        raise OSError("closed")

    channel.send = send
    _open_fake_shell(monkeypatch, "sid-swap", channel)
    assert send_input("sid-swap", "a") is None


def test_a_send_error_on_the_open_shell_is_a_failure(monkeypatch):
    channel = _Channel([])

    def send(data):
        raise OSError("closed")

    channel.send = send
    _open_fake_shell(monkeypatch, "sid-os", channel)
    assert send_input("sid-os", "a") is False
    close_terminal("sid-os")


def test_a_closed_send_is_a_failure(monkeypatch):
    channel = _Channel([])
    channel.send = lambda data: 0
    _open_fake_shell(monkeypatch, "sid-closed", channel)
    assert send_input("sid-closed", "a") is False
    close_terminal("sid-closed")


def test_a_full_send_window_is_retried(monkeypatch):
    channel = _Channel([])
    calls = {"n": 0}

    def send(data):
        calls["n"] += 1
        if calls["n"] < 3:
            raise TimeoutError("window")
        return len(data)

    channel.send = send
    _open_fake_shell(monkeypatch, "sid-window", channel)
    assert send_input("sid-window", "a") is True
    close_terminal("sid-window")
    assert calls["n"] == 3


def test_a_stuck_send_window_drops_the_keystroke(monkeypatch):
    channel = _Channel([])

    def send(data):
        raise TimeoutError("window")

    channel.send = send
    _open_fake_shell(monkeypatch, "sid-stuck", channel)
    assert send_input("sid-stuck", "a") is None
    assert send_input("sid-stuck", "b") is None
    close_terminal("sid-stuck")


def test_a_split_character_is_reassembled(monkeypatch):
    sent = []
    channel = _Channel([b"\xc3", b"\xa9"])
    channel.recv_ready = lambda: True

    def recv(size):
        if channel.chunks:
            return channel.chunks.pop(0)
        channel.closed = True
        return b""

    channel.recv = recv

    class Client(_Client):
        def __init__(self):
            super().__init__()
            self.channel = channel

    monkeypatch.setattr(
        "api.ssh_terminal.reservation_info",
        lambda socket_username, requested, node_name, now: {
            "reservation_id": "res-1",
            "username": socket_username,
            "node_name": node_name,
        },
    )
    monkeypatch.setattr(
        "api.ssh_terminal.load_terminal_endpoint",
        lambda username, node_name, now: ("res-1", 3000, "token"),
    )
    monkeypatch.setattr("api.ssh_terminal.decrypt_machine_password", lambda token: "secret-db")
    monkeypatch.setattr("api.ssh_terminal._ssh_client", lambda username, port, password: Client())
    assert open_terminal("ada", "ada", "pool-node-1", 10, "sid-utf") is None
    start_output("sid-utf", sent.append)
    for _ in range(50):
        if sent and channel.closed:
            break
        time.sleep(0.01)
    close_terminal("sid-utf")
    assert sent == ["é"]


def test_the_input_event_hides_a_send_failure(monkeypatch):
    emitted = {}

    async def emit(event, body, to):
        emitted["event"] = event
        emitted["body"] = body
        emitted["to"] = to

    def fail(sid, data):
        raise RuntimeError(data)

    monkeypatch.setattr("api.terminal_socket.sio.emit", emit)
    monkeypatch.setattr("api.terminal_socket.send_input", fail)
    asyncio.run(terminal_input("sid", {"data": "secret-keystroke"}))
    assert emitted["event"] == "error"
    assert emitted["body"] == {"message": TERMINAL_OPEN_FAILED}
    assert emitted["to"] == "sid"
    assert "secret-keystroke" not in str(emitted["body"])


def test_the_reader_closes_the_client_when_the_channel_ends(monkeypatch):
    sent = []
    channel = _Channel([b"bye"])
    channel.recv_ready = lambda: True

    def recv(size):
        if channel.chunks:
            return channel.chunks.pop(0)
        return b""

    channel.recv = recv
    held = {}

    class Client(_Client):
        def __init__(self):
            super().__init__()
            self.channel = channel

    def client(username, port, password):
        held["client"] = Client()
        return held["client"]

    monkeypatch.setattr(
        "api.ssh_terminal.reservation_info",
        lambda socket_username, requested, node_name, now: {
            "reservation_id": "res-1",
            "username": socket_username,
            "node_name": node_name,
        },
    )
    monkeypatch.setattr(
        "api.ssh_terminal.load_terminal_endpoint",
        lambda username, node_name, now: ("res-1", 3000, "token"),
    )
    monkeypatch.setattr("api.ssh_terminal.decrypt_machine_password", lambda token: "secret-db")
    monkeypatch.setattr("api.ssh_terminal._ssh_client", client)
    assert open_terminal("ada", "ada", "pool-node-1", 10, "sid-end") is None
    start_output("sid-end", sent.append)
    for _ in range(50):
        if sent and held["client"].closed:
            break
        time.sleep(0.01)
    assert sent == ["bye"]
    assert held["client"].closed is True


def _patch_shell(monkeypatch, client_factory):
    monkeypatch.setattr(
        "api.ssh_terminal.reservation_info",
        lambda socket_username, requested, node_name, now: {
            "reservation_id": "res-1",
            "username": socket_username,
            "node_name": node_name,
        },
    )
    monkeypatch.setattr(
        "api.ssh_terminal.load_terminal_endpoint",
        lambda username, node_name, now: ("res-1", 3000, "token"),
    )
    monkeypatch.setattr("api.ssh_terminal.decrypt_machine_password", lambda token: "secret-db")
    monkeypatch.setattr("api.ssh_terminal._ssh_client", client_factory)


def test_a_read_timeout_keeps_the_shell_open(monkeypatch):
    channel = _Channel([])

    def recv_ready():
        raise TimeoutError("idle")

    channel.recv_ready = recv_ready
    held = {}

    class Client(_Client):
        def __init__(self):
            super().__init__()
            self.channel = channel

    def client(username, port, password):
        held["client"] = Client()
        return held["client"]

    _patch_shell(monkeypatch, client)
    assert open_terminal("ada", "ada", "pool-node-1", 10, "sid-idle") is None
    start_output("sid-idle", lambda text: None)
    time.sleep(0.05)
    assert held["client"].closed is False
    close_terminal("sid-idle")
    assert held["client"].closed is True


def test_a_read_failure_closes_the_shell(monkeypatch):
    channel = _Channel([])

    def recv_ready():
        raise RuntimeError("dead")

    channel.recv_ready = recv_ready
    held = {}

    class Client(_Client):
        def __init__(self):
            super().__init__()
            self.channel = channel

    def client(username, port, password):
        held["client"] = Client()
        return held["client"]

    _patch_shell(monkeypatch, client)
    assert open_terminal("ada", "ada", "pool-node-1", 10, "sid-dead") is None
    start_output("sid-dead", lambda text: None)
    for _ in range(50):
        if held["client"].closed:
            break
        time.sleep(0.01)
    assert held["client"].closed is True


def test_the_old_reader_does_not_close_the_replacement_shell(monkeypatch):
    clients = []

    class Client(_Client):
        def __init__(self):
            super().__init__()
            self.channel = _Channel([])

    def client(username, port, password):
        made = Client()
        clients.append(made)
        return made

    monkeypatch.setattr(
        "api.ssh_terminal.reservation_info",
        lambda socket_username, requested, node_name, now: {
            "reservation_id": "res-1",
            "username": socket_username,
            "node_name": node_name,
        },
    )
    monkeypatch.setattr(
        "api.ssh_terminal.load_terminal_endpoint",
        lambda username, node_name, now: ("res-1", 3000, "token"),
    )
    monkeypatch.setattr("api.ssh_terminal.decrypt_machine_password", lambda token: "secret-db")
    monkeypatch.setattr("api.ssh_terminal._ssh_client", client)
    assert open_terminal("ada", "ada", "pool-node-1", 10, "sid-swap") is None
    start_output("sid-swap", lambda text: None)
    assert open_terminal("ada", "ada", "pool-node-1", 10, "sid-swap") is None
    time.sleep(0.05)
    assert clients[0].closed is True
    assert clients[1].closed is False
    close_terminal("sid-swap")
    assert clients[1].closed is True


def test_a_cancelled_open_does_not_start_a_reader(monkeypatch):
    emitted = []
    started = []

    async def get_session(sid):
        return {"username": "ada"}

    async def emit(event, body, to):
        emitted.append((event, body, to))

    monkeypatch.setattr("api.terminal_socket.sio.get_session", get_session)
    monkeypatch.setattr("api.terminal_socket.sio.emit", emit)
    monkeypatch.setattr("api.terminal_socket.open_terminal", lambda *args: OPEN_CANCELLED)
    monkeypatch.setattr("api.terminal_socket.start_output", lambda *args: started.append(args))

    asyncio.run(connect_ssh("sid", {"username": "ada", "node_name": "pool-node-1"}))
    assert emitted == []
    assert started == []


def test_an_unexpected_open_failure_stays_a_fixed_message(monkeypatch):
    emitted = {}

    async def get_session(sid):
        return {"username": "ada"}

    async def emit(event, body, to):
        emitted["event"] = event
        emitted["body"] = body
        emitted["to"] = to

    def boom(*args):
        raise RuntimeError("secret-db")

    monkeypatch.setattr("api.terminal_socket.sio.get_session", get_session)
    monkeypatch.setattr("api.terminal_socket.sio.emit", emit)
    monkeypatch.setattr("api.terminal_socket.open_terminal", boom)

    asyncio.run(connect_ssh("sid", {"username": "ada", "node_name": "pool-node-1"}))
    assert emitted["event"] == "error"
    assert emitted["body"] == {"message": TERMINAL_OPEN_FAILED}
    assert emitted["to"] == "sid"
    assert "secret-db" not in str(emitted["body"])


def test_a_lookup_failure_clears_the_connecting_mark(monkeypatch):
    from api.errors import DatabaseUnavailable

    calls = {"n": 0}

    def info(*_args):
        calls["n"] += 1
        if calls["n"] == 1:
            raise DatabaseUnavailable("down")
        return {
            "reservation_id": "res-1",
            "username": "ada",
            "node_name": "pool-node-1",
        }

    monkeypatch.setattr("api.ssh_terminal.reservation_info", info)
    monkeypatch.setattr(
        "api.ssh_terminal.load_terminal_endpoint",
        lambda username, node_name, now: ("res-1", 3000, "token"),
    )
    monkeypatch.setattr("api.ssh_terminal.decrypt_machine_password", lambda token: "secret-db")
    monkeypatch.setattr(
        "api.ssh_terminal._ssh_client",
        lambda username, port, password: _Client(),
    )
    try:
        open_terminal("ada", "ada", "pool-node-1", 10, "sid-clear")
        raised = False
    except DatabaseUnavailable:
        raised = True
    assert raised
    assert send_input("sid-clear", "a") is None
    assert open_terminal("ada", "ada", "pool-node-1", 10, "sid-clear") is None
    close_terminal("sid-clear")
    assert calls["n"] == 2


def test_a_logout_during_lookup_stays_quiet(monkeypatch):
    def info(*_args):
        close_terminal("sid-quiet")
        return {"error": TERMINAL_NO_RESERVATION}

    monkeypatch.setattr("api.ssh_terminal.reservation_info", info)
    assert open_terminal("ada", "ada", "pool-node-1", 10, "sid-quiet") is OPEN_CANCELLED
    assert send_input("sid-quiet", "a") is None


def test_a_disconnect_during_connect_closes_the_new_client(monkeypatch):
    held = {}

    def client(username, port, password):
        close_terminal("sid-1")
        held["client"] = _Client()
        return held["client"]

    monkeypatch.setattr(
        "api.ssh_terminal.reservation_info",
        lambda socket_username, requested, node_name, now: {
            "reservation_id": "res-1",
            "username": socket_username,
            "node_name": node_name,
        },
    )
    monkeypatch.setattr(
        "api.ssh_terminal.load_terminal_endpoint",
        lambda username, node_name, now: ("res-1", 3000, "token"),
    )
    monkeypatch.setattr("api.ssh_terminal.decrypt_machine_password", lambda token: "secret-db")
    monkeypatch.setattr("api.ssh_terminal._ssh_client", client)

    assert open_terminal("ada", "ada", "pool-node-1", 10, "sid-1") is OPEN_CANCELLED
    assert held["client"].closed is True


def test_ssh_does_not_connect_for_someone_else(monkeypatch):
    def fail(*_args, **_kwargs):
        raise AssertionError("SSH was opened")

    monkeypatch.setattr("api.ssh_terminal._ssh_client", fail)
    body = open_terminal("ada", "grace", "pool-node-1", 10, "sid-1")
    assert body == {"error": TERMINAL_UNAUTHORIZED}
    assert "password" not in body


def test_a_failed_shell_does_not_report_the_password(monkeypatch):
    monkeypatch.setattr(
        "api.ssh_terminal.reservation_info",
        lambda socket_username, requested, node_name, now: {
            "reservation_id": "res-1",
            "username": socket_username,
            "node_name": node_name,
        },
    )
    monkeypatch.setattr(
        "api.ssh_terminal.load_terminal_endpoint",
        lambda username, node_name, now: ("res-1", 3000, "token"),
    )
    monkeypatch.setattr("api.ssh_terminal.decrypt_machine_password", lambda token: "secret-db")

    def fail(username, port, password):
        raise RuntimeError("boom")

    monkeypatch.setattr("api.ssh_terminal._ssh_client", fail)
    body = open_terminal("ada", "ada", "pool-node-1", 10, "sid-1")
    assert body == {"error": TERMINAL_OPEN_FAILED}
    assert "secret-db" not in body["error"]


def test_a_missing_endpoint_is_not_an_open_terminal(monkeypatch):
    monkeypatch.setattr(
        "api.ssh_terminal.reservation_info",
        lambda socket_username, requested, node_name, now: {
            "reservation_id": "res-1",
            "username": socket_username,
            "node_name": node_name,
        },
    )
    monkeypatch.setattr(
        "api.ssh_terminal.load_terminal_endpoint",
        lambda username, node_name, now: None,
    )
    assert open_terminal("ada", "ada", "pool-node-1", 10, "sid") == {
        "error": TERMINAL_NO_RESERVATION
    }
    assert send_input("sid", "a") is None
