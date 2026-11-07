import logging
import threading
import time

import psycopg

from api.containers import remove_container_user
from api.db import connect
from api.errors import DatabaseUnavailable
from api.node_cleanup import detach_nodes
from api.pool_sql import (
    free_allocated_node,
    list_expired_allocated_names,
    lock_pool_node,
    next_node_expiry,
)
from api.reservation_sql import (
    active_reservation_uses_node,
    list_due_reservations,
    lock_owned_reservation,
    mark_if_active,
    next_reservation_expiry,
    node_names,
)

logger = logging.getLogger(__name__)

_stop = threading.Event()
_thread: threading.Thread | None = None


def expire_due(now: float | None = None) -> int:
    """Mark due reservations expired and free leftover allocated nodes."""
    current = time.time() if now is None else now
    count = 0
    for row in _due_reservations(current):
        if _expire_one(row["id"], row["username"], current):
            count += 1
    count += _free_orphans(current)
    return count


def sleep_seconds(deadline: float | None, now: float) -> float:
    """Wait until the next deadline, but never less than 1s or more than 30s."""
    if deadline is None:
        return 30
    return max(1, min(30, deadline - now))


def expiry_loop(stop: threading.Event) -> None:
    while not stop.is_set():
        try:
            expire_due()
            delay = sleep_seconds(_next_deadline(), time.time())
        except Exception:
            logger.exception("expiry check failed")
            delay = 30
        stop.wait(delay)


def start_expiry_thread() -> None:
    """Start the daemon loop once. Tests leave ODP_EXPIRY_THREAD at 0."""
    import os

    global _thread
    if os.environ.get("ODP_EXPIRY_THREAD", "1") == "0":
        return
    if _thread is not None and _thread.is_alive():
        return
    _stop.clear()
    _thread = threading.Thread(target=expiry_loop, args=(_stop,), name="odp-expiry", daemon=True)
    _thread.start()


def stop_expiry_thread() -> None:
    _stop.set()


def _due_reservations(now: float) -> list[dict]:
    return list_due_reservations(now)


def _expire_one(reservation_id: str, username: str, now: float) -> bool:
    committed = False
    skipped = False
    try:
        with connect() as conn:
            row = lock_owned_reservation(conn, reservation_id, username)
            due = (
                row is not None
                and row["status"] == "active"
                and now > float(row["expires_at"])
            )
            if not due:
                conn.rollback()
                skipped = True
            else:
                detach_nodes(conn, username, node_names(row["nodes"]))
                mark_if_active(conn, reservation_id, "expired")
                conn.commit()
                committed = True
    except (psycopg.OperationalError, psycopg.InterfaceError) as exc:
        if committed:
            logger.exception(
                "reservation %s was expired but the database connection failed while closing",
                reservation_id,
            )
            return True
        if skipped:
            return False
        raise DatabaseUnavailable from exc
    return not skipped


def _free_orphans(now: float) -> int:
    return sum(_free_orphan(name, now) for name in list_expired_allocated_names(now))


def _free_orphan(name: str, now: float) -> bool:
    committed = False
    skipped = False
    try:
        with connect() as conn:
            row = lock_pool_node(conn, name)
            due = (
                row is not None
                and row["status"] == "allocated"
                and row["expiry"]
                and now > float(row["expiry"])
                and not active_reservation_uses_node(conn, name)
            )
            if not due:
                conn.rollback()
                skipped = True
            else:
                owner = row["owner"]
                if isinstance(owner, str) and owner:
                    remove_container_user(name, owner)
                free_allocated_node(conn, name)
                conn.commit()
                committed = True
    except (psycopg.OperationalError, psycopg.InterfaceError) as exc:
        if committed:
            logger.exception("node %s was freed but the database connection failed while closing", name)
            return True
        if skipped:
            return False
        raise DatabaseUnavailable from exc
    return not skipped


def _next_deadline() -> float | None:
    deadlines = [
        deadline
        for deadline in (next_reservation_expiry(), next_node_expiry())
        if deadline is not None
    ]
    if not deadlines:
        return None
    return min(deadlines)
