"""Open one SSH session. The machine password never leaves this module."""

import codecs
import logging
import threading
import time

from api.machine_passwords import decrypt_machine_password
from api.reservation_sql import load_terminal_endpoint
from api.terminal_access import (
    TERMINAL_NO_RESERVATION,
    reservation_info,
)

logger = logging.getLogger(__name__)
TERMINAL_OPEN_FAILED = "Could not open the terminal"


class _Pending:
    """Marks a connect that has not stored its client yet."""


class _OpenCancelled:
    """This attempt lost the socket. Do not report success or failure."""


OPEN_CANCELLED = _OpenCancelled()
_sessions: dict[str, object] = {}
_closed_sids: set[str] = set()
_expired_sids: set[str] = set()
_lock = threading.Lock()
_CONNECTING = object()
_claim = threading.Lock()


def open_terminal(
    socket_username: str,
    requested_username,
    node_name,
    now: float,
    sid: str,
    cols=None,
    rows=None,
):
    """Connect SSH for this socket.

    None means this socket owns a shell. OPEN_CANCELLED means the socket
    went away or a newer connect replaced this attempt. An error dict is
    the only result the browser should see.
    """
    waiting = _wait_if_idle(sid)
    if waiting is _CONNECTING:
        return OPEN_CANCELLED
    try:
        return _open_reserved(
            socket_username,
            requested_username,
            node_name,
            now,
            sid,
            cols,
            rows,
            waiting,
        )
    finally:
        if isinstance(waiting, _Pending):
            _cancel(sid, waiting)


def _open_reserved(
    socket_username,
    requested_username,
    node_name,
    now,
    sid,
    cols,
    rows,
    waiting,
):
    """Finish a connect that already owns the empty slot, or is replacing a shell."""
    try:
        info = reservation_info(socket_username, requested_username, node_name, now)
    except Exception:
        if _abandoned(sid, waiting):
            return OPEN_CANCELLED
        raise
    if "error" in info:
        if _abandoned(sid, waiting):
            return OPEN_CANCELLED
        return info
    try:
        endpoint = load_terminal_endpoint(socket_username, node_name, now)
    except Exception:
        if _abandoned(sid, waiting):
            return OPEN_CANCELLED
        raise
    if endpoint is None:
        if _abandoned(sid, waiting):
            return OPEN_CANCELLED
        return {"error": TERMINAL_NO_RESERVATION}
    _reservation_id, port, token = endpoint[0], endpoint[1], endpoint[2]
    expires_at = float(endpoint[3]) if len(endpoint) > 3 else None
    current = None if waiting is not None else _shell(sid)
    try:
        password = decrypt_machine_password(token)
        client = _ssh_client(socket_username, port, password)
        client.expires_at = expires_at
    except Exception:
        logger.exception("could not open a terminal for %s", socket_username)
        if _abandoned(sid, waiting):
            return OPEN_CANCELLED
        return {"error": TERMINAL_OPEN_FAILED}
    if waiting is not None:
        if not _finish(sid, waiting, client):
            client.close()
            return OPEN_CANCELLED
    elif not _swap_shell(sid, current, client):
        client.close()
        return OPEN_CANCELLED
    else:
        _close_shell(current)
    try:
        resize_terminal(sid, cols, rows)
    except Exception:
        logger.exception("could not set the initial terminal size")
    return None


def start_output(sid: str, emit, on_expired=None) -> None:
    """Forward shell output until this shell is replaced or closed."""
    shell = _shell(sid)
    if shell is None:
        return
    threading.Thread(
        target=_read_output,
        args=(sid, shell, emit, on_expired),
        name="odp-ssh-output",
        daemon=True,
    ).start()


def send_input(sid: str, data: str) -> bool | None:
    """Write keystrokes to this socket's shell.

    None means the keystroke is dropped: no shell has been opened yet,
    SSH is still connecting, or the send window stayed full.
    False means a shell was open and is now gone.
    """
    for _ in range(3):
        with _claim:
            lock, state, shell = _writer_lock(sid)
            if lock is None:
                return _idle_keystroke(sid, state)
            owned = lock.acquire(blocking=False)
        if not owned:
            lock.acquire()
        try:
            if _shell(sid) is not shell:
                continue
            return _send_input(sid, shell, data)
        finally:
            lock.release()
    return None


def _send_input(sid: str, shell, data: str) -> bool | None:
    channel = _open_channel(shell)
    if channel is None:
        return _send_result(sid, shell)
    payload = data.encode("utf-8")
    waits = 0
    while payload:
        try:
            sent = channel.send(payload)
        except TimeoutError:
            waits += 1
            if waits > 50:
                if _open_channel(shell) is None:
                    return _send_result(sid, shell)
                return None
            time.sleep(0.01)
            continue
        except Exception:
            logger.exception("could not send a keystroke for %s", sid)
            return _send_result(sid, shell)
        if sent <= 0:
            return _send_result(sid, shell)
        waits = 0
        payload = payload[sent:]
    return _send_outcome(sid, shell, True)


def _send_result(sid: str, shell) -> bool | None:
    """False when this shell ended. None when a newer shell replaced it."""
    return _send_outcome(sid, shell, False)


def _send_outcome(sid: str, shell, sent: bool) -> bool | None:
    if _reservation_expired(sid):
        return True if sent else None
    current = _shell(sid)
    if current is shell:
        return True if sent else False
    if current is None and _shell_ended(sid):
        return True if sent else False
    return None


def _shell_ended(sid: str) -> bool:
    with _lock:
        return sid in _closed_sids


def _reservation_expired(sid: str) -> bool:
    with _lock:
        return sid in _expired_sids


def resize_terminal(sid: str, cols, rows) -> None:
    """Resize this socket's shell. Bad sizes and a missing shell are ignored."""
    if isinstance(cols, bool) or isinstance(rows, bool):
        return
    if not isinstance(cols, int) or not isinstance(rows, int):
        return
    if cols < 1 or rows < 1 or cols > 1000 or rows > 1000:
        return
    for _ in range(3):
        with _claim:
            lock, _state, shell = _writer_lock(sid)
            if lock is None:
                return
            owned = lock.acquire(blocking=False)
        if not owned:
            lock.acquire()
        try:
            if _shell(sid) is not shell:
                continue
            channel = _open_channel(shell)
            if channel is None:
                return
            channel.resize_pty(width=cols, height=rows)
            return
        finally:
            lock.release()


def close_terminal(sid: str) -> None:
    """Close the SSH client stored for this socket, if any."""
    with _lock:
        client = _sessions.pop(sid, None)
        _closed_sids.discard(sid)
        _expired_sids.discard(sid)
    if client is None or isinstance(client, _Pending):
        return
    try:
        client.close()
    except Exception:
        logger.exception("could not close a terminal")


def _idle_keystroke(sid: str, state: str) -> bool | None:
    """Drop a key before any shell exists. Fail only after one has ended."""
    if state == "pending":
        return None
    with _lock:
        if sid in _expired_sids:
            return None
        ended = sid in _closed_sids
    return False if ended else None


def _writer_lock(sid: str):
    """The shell's writer lock together with that shell."""
    with _lock:
        client = _sessions.get(sid)
        if client is None:
            return None, "gone", None
        if isinstance(client, _Pending):
            return None, "pending", None
        writer = getattr(client, "io_lock", None)
        if writer is None:
            writer = threading.Lock()
            client.io_lock = writer
        return writer, "open", client


def _wait_if_idle(sid: str) -> _Pending | None | object:
    """Mark an empty socket as connecting. A live shell stays open."""
    token = _Pending()
    with _lock:
        current = _sessions.get(sid)
        if isinstance(current, _Pending):
            return _CONNECTING
        if current is not None:
            return None
        _sessions[sid] = token
    return token


def _swap_shell(sid: str, expected, client) -> bool:
    """Store client only while this live shell is still the current one."""
    with _lock:
        if expected is None or isinstance(expected, _Pending):
            return False
        if _sessions.get(sid) is not expected:
            return False
        _sessions[sid] = client
        _closed_sids.discard(sid)
        _expired_sids.discard(sid)
        return True


def _close_shell(previous) -> None:
    if previous is None or isinstance(previous, _Pending):
        return
    try:
        previous.close()
    except Exception:
        logger.exception("could not close the previous terminal")


def _finish(sid: str, token: _Pending, client) -> bool:
    with _lock:
        if _sessions.get(sid) is not token:
            return False
        _sessions[sid] = client
        _closed_sids.discard(sid)
        _expired_sids.discard(sid)
        return True


def _cancel(sid: str, token: _Pending) -> None:
    with _lock:
        if _sessions.get(sid) is token:
            _sessions.pop(sid, None)


def _abandoned(sid: str, waiting) -> bool:
    """True when logout already cleared the slot this attempt reserved."""
    if not isinstance(waiting, _Pending):
        return False
    with _lock:
        return _sessions.get(sid) is not waiting


def _read_output(sid: str, shell, emit, on_expired) -> None:
    decode = codecs.getincrementaldecoder("utf-8")("ignore")
    while _shell(sid) is shell:
        if _shell_expired(shell):
            _end_shell(sid, shell, on_expired)
            return
        channel = _open_channel(shell)
        if channel is None:
            _end_shell(sid, shell, on_expired)
            return
        try:
            if not channel.recv_ready():
                time.sleep(0.01)
                continue
            data = channel.recv(4096)
        except TimeoutError:
            # settimeout(0) raises this when recv_ready raced ahead of the data.
            time.sleep(0.01)
            continue
        except Exception:
            logger.exception("ssh output stopped for %s", sid)
            _end_shell(sid, shell, on_expired)
            return
        if not data:
            _end_shell(sid, shell, on_expired)
            return
        text = decode.decode(data)
        if text:
            emit(text)


def _shell(sid: str):
    with _lock:
        client = _sessions.get(sid)
    if client is None or isinstance(client, _Pending):
        return None
    return client


def _shell_expired(shell) -> bool:
    deadline = getattr(shell, "expires_at", None)
    return (
        isinstance(deadline, (int, float))
        and not isinstance(deadline, bool)
        and time.time() > deadline
    )


def _open_channel(shell):
    channel = getattr(shell, "channel", None)
    if channel is None or getattr(channel, "closed", False):
        return None
    return channel


def _end_shell(sid: str, shell, on_expired) -> None:
    """Close this shell. Say the reservation expired when the deadline has passed."""
    if _shell(sid) is not shell:
        return
    if not _shell_expired(shell):
        _close_if_current(sid, shell)
        return
    with _lock:
        _expired_sids.add(sid)
    try:
        if on_expired is not None:
            on_expired()
    except Exception:
        logger.exception("could not report an expired terminal for %s", sid)
        with _lock:
            _expired_sids.discard(sid)
    finally:
        _close_if_current(sid, shell)


def _close_if_current(sid: str, shell) -> None:
    """Close this shell only when a newer connect has not replaced it."""
    with _lock:
        if _sessions.get(sid) is not shell:
            return
        _sessions.pop(sid, None)
        _closed_sids.add(sid)
    try:
        shell.close()
    except Exception:
        logger.exception("could not close a terminal")


class _Shell:
    def __init__(self, client, channel):
        self.client = client
        self.channel = channel

    def close(self):
        try:
            self.channel.close()
        except Exception:
            pass
        try:
            self.client.close()
        except Exception:
            pass


def _ssh_client(username: str, port: int, password: str):
    import paramiko

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            "127.0.0.1",
            port=port,
            username=username,
            password=password,
            timeout=10,
            look_for_keys=False,
            allow_agent=False,
        )
        channel = client.invoke_shell(term="xterm", width=80, height=24)
        channel.settimeout(0)
    except Exception:
        client.close()
        raise
    return _Shell(client, channel)
