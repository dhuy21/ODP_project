"""Socket.IO terminal gate."""

import asyncio
import logging
import time

import socketio

from api.errors import DatabaseUnavailable
from api.expiry import start_expiry_thread, stop_expiry_thread
from api.responses import DATABASE_UNAVAILABLE
from api.socket_session import username_from_cookie_header
from api.ssh_terminal import (
    OPEN_CANCELLED,
    TERMINAL_OPEN_FAILED,
    close_terminal,
    open_terminal,
    resize_terminal,
    send_input,
    start_output,
)
from api.terminal_access import TERMINAL_UNAUTHORIZED, reservation_info
from api.user_sql import find_user_role

logger = logging.getLogger(__name__)
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins=[])
TERMINAL_SIGNED_OUT = "Signed out"
_close_guard = asyncio.Lock()


@sio.event
async def connect(sid, environ):
    username = username_from_cookie_header(environ.get("HTTP_COOKIE"))
    if username is None:
        return False
    try:
        role = await asyncio.to_thread(find_user_role, username)
    except DatabaseUnavailable:
        logger.exception("could not check the socket account %s", username)
        return False
    if role is None:
        return False
    await sio.save_session(sid, {"username": username})
    await sio.enter_room(sid, username)


@sio.on("request_reservation_info")
async def request_reservation_info(sid, data):
    username = await _socket_username(sid)
    if username is None:
        await sio.emit("reservation_info", {"error": TERMINAL_UNAUTHORIZED}, to=sid)
        return
    payload = data if isinstance(data, dict) else {}
    try:
        body = await asyncio.to_thread(
            reservation_info,
            username,
            payload.get("username"),
            payload.get("node_name"),
            time.time(),
        )
    except DatabaseUnavailable:
        logger.exception("could not look up a terminal reservation for %s", username)
        body = {"error": DATABASE_UNAVAILABLE}
    except Exception:
        logger.exception("could not look up a terminal reservation for %s", username)
        body = {"error": TERMINAL_OPEN_FAILED}
    await sio.emit("reservation_info", body, to=sid)


@sio.on("connect_ssh")
async def connect_ssh(sid, data):
    username = await _socket_username(sid)
    if username is None:
        await sio.emit("error", {"message": TERMINAL_UNAUTHORIZED}, to=sid)
        return
    payload = data if isinstance(data, dict) else {}
    try:
        body = await asyncio.to_thread(
            open_terminal,
            username,
            payload.get("username"),
            payload.get("node_name"),
            time.time(),
            sid,
            payload.get("cols"),
            payload.get("rows"),
        )
    except DatabaseUnavailable:
        logger.exception("could not open a terminal for %s", username)
        body = {"error": DATABASE_UNAVAILABLE}
    except Exception:
        logger.exception("could not open a terminal for %s", username)
        body = {"error": TERMINAL_OPEN_FAILED}
    if body is None:
        loop = asyncio.get_running_loop()
        start_output(
            sid,
            lambda text: _send_output(loop, sid, text),
            lambda: _send_expired(loop, sid),
        )
        return
    if body is OPEN_CANCELLED:
        return
    await sio.emit("error", {"message": body.get("error") or TERMINAL_OPEN_FAILED}, to=sid)


@sio.on("input")
async def terminal_input(sid, data):
    payload = data if isinstance(data, dict) else {}
    keystrokes = payload.get("data")
    if not isinstance(keystrokes, str) or keystrokes == "":
        return
    try:
        sent = await asyncio.to_thread(send_input, sid, keystrokes)
    except Exception:
        logger.exception("could not send terminal input for %s", sid)
        await sio.emit("error", {"message": TERMINAL_OPEN_FAILED}, to=sid)
        return
    if sent is None:
        return
    if not sent:
        await sio.emit("error", {"message": TERMINAL_OPEN_FAILED}, to=sid)


@sio.on("resize")
async def terminal_resize(sid, data):
    payload = data if isinstance(data, dict) else {}
    try:
        await asyncio.to_thread(
            resize_terminal,
            sid,
            payload.get("cols"),
            payload.get("rows"),
        )
    except Exception:
        logger.exception("could not resize the terminal for %s", sid)


@sio.event
async def disconnect(sid):
    await asyncio.to_thread(close_terminal, sid)


async def close_user_terminals(username: str) -> None:
    """Tell this user's open terminals they signed out, then drop the sockets."""
    async with _close_guard:
        await _close_user_terminals(username)


async def _close_user_terminals(username: str) -> None:
    told = False
    for _ in range(3):
        sids = [sid for sid, _transport in sio.manager.get_participants("/", username)]
        if not sids:
            return
        if not told:
            await sio.emit(
                "force_disconnect",
                {"message": TERMINAL_SIGNED_OUT},
                room=username,
            )
            told = True
        for sid in sids:
            await asyncio.to_thread(close_terminal, sid)
            await sio.disconnect(sid)


def _send_expired(loop, sid: str) -> None:
    _schedule(loop, sid, sio.emit("force_disconnect", {"message": "Reservation expired"}, to=sid))


def _send_output(loop, sid: str, text: str) -> None:
    if text == "":
        return
    _schedule(loop, sid, sio.emit("output", {"data": text}, to=sid))


def _schedule(loop, sid: str, coroutine) -> None:
    future = asyncio.run_coroutine_threadsafe(coroutine, loop)

    def _logged(done):
        try:
            done.result()
        except Exception:
            logger.exception("could not send ssh output to %s", sid)

    future.add_done_callback(_logged)


async def _socket_username(sid):
    session = await sio.get_session(sid)
    username = session.get("username") if isinstance(session, dict) else None
    if not isinstance(username, str) or username == "":
        return None
    return username


def wrap_fastapi(fastapi_app):
    """Serve Socket.IO and the HTTP API from one process.

    The Engine.IO wrapper handles lifespan itself, so the expiry thread is
    started here as well as on the FastAPI app.
    """
    return socketio.ASGIApp(
        sio,
        fastapi_app,
        on_startup=start_expiry_thread,
        on_shutdown=stop_expiry_thread,
    )
