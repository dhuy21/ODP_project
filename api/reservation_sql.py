"""SQL for reservations. Callers own the transaction, except the helpers that open one."""

import logging
import time
import uuid

import psycopg
from psycopg.types.json import Json

from api.db import connect, fetch_all
from api.errors import DatabaseUnavailable

logger = logging.getLogger(__name__)

_CLOSE_STATUS = {"released": "released", "expired": "expired"}


def node_names(nodes) -> list[str]:
    """Names stored in reservations.nodes. Entries without a name are ignored."""
    if not isinstance(nodes, list):
        return []
    names = []
    for node in nodes:
        if isinstance(node, dict) and isinstance(node.get("name"), str) and node["name"]:
            names.append(node["name"])
    return names


def lock_owned_reservation(conn, reservation_id: str, username: str):
    """Lock one reservation row owned by this user. None when it is not theirs."""
    return conn.execute(
        """
        SELECT r.status, r.expires_at, r.nodes
        FROM reservations AS r
        JOIN users AS u ON r.user_id = u.id
        WHERE r.id = %s AND u.username = %s
        FOR UPDATE OF r
        """,
        (reservation_id, username),
    ).fetchone()


def lock_active_reservations(conn, user_id: int):
    """Lock every active reservation of one account."""
    return conn.execute(
        """
        SELECT id, nodes
        FROM reservations
        WHERE user_id = %s AND status = 'active'
        FOR UPDATE
        """,
        (user_id,),
    ).fetchall()


def lock_reservation(conn, reservation_id: str):
    """Lock one reservation and its owner. None when the id does not exist."""
    return conn.execute(
        """
        SELECT u.username, r.nodes
        FROM reservations AS r
        JOIN users AS u ON r.user_id = u.id
        WHERE r.id = %s
        FOR UPDATE OF r
        """,
        (reservation_id,),
    ).fetchone()


def mark_deleted(conn, reservation_id: str) -> None:
    """Soft-delete one reservation. The status literal is not user input."""
    conn.execute(
        """
        UPDATE reservations
        SET status = 'deleted'
        WHERE id = %s
        """,
        (reservation_id,),
    )


def mark_if_active(conn, reservation_id: str, status: str) -> None:
    """Set status only while the row is still active. status is not user input."""
    literal = _CLOSE_STATUS[status]
    conn.execute(
        f"""
        UPDATE reservations
        SET status = '{literal}'
        WHERE id = %s AND status = 'active'
        """,
        (reservation_id,),
    )


def list_due_reservations(now: float) -> list[dict]:
    return fetch_all(
        """
        SELECT r.id, u.username
        FROM reservations AS r
        JOIN users AS u ON r.user_id = u.id
        WHERE r.status = 'active' AND r.expires_at > 0 AND r.expires_at < %s
        ORDER BY r.expires_at ASC, r.id ASC
        """,
        (now,),
    )


def find_active_terminal_reservation(username: str, node_name: str, now: float) -> str | None:
    """Id of an active, unexpired reservation that still lists this node.

    The machine password is not selected.
    """
    rows = fetch_all(
        """
        SELECT r.id
        FROM reservations AS r
        JOIN users AS u ON r.user_id = u.id
        WHERE u.username = %s
          AND r.status = 'active'
          AND r.expires_at > %s
          AND jsonb_typeof(COALESCE(r.nodes, '[]'::jsonb)) = 'array'
          AND EXISTS (
              SELECT 1
              FROM jsonb_array_elements(r.nodes) AS node
              WHERE node->>'name' = %s
          )
        ORDER BY r.created_at DESC, r.id ASC
        LIMIT 1
        """,
        (username, now, node_name),
    )
    if not rows:
        return None
    return str(rows[0]["id"])


def load_terminal_endpoint(username: str, node_name: str, now: float):
    """Port and encrypted machine password for one active node.

    The caller decrypts the password and must not return it to the browser.
    """
    rows = fetch_all(
        """
        SELECT r.id,
               (
                   SELECT node->>'port'
                   FROM jsonb_array_elements(r.nodes) AS node
                   WHERE node->>'name' = %s
                   LIMIT 1
               ) AS port,
               r.vm_password_encrypted,
               r.expires_at
        FROM reservations AS r
        JOIN users AS u ON r.user_id = u.id
        WHERE u.username = %s
          AND r.status = 'active'
          AND r.expires_at > %s
          AND jsonb_typeof(COALESCE(r.nodes, '[]'::jsonb)) = 'array'
          AND EXISTS (
              SELECT 1
              FROM jsonb_array_elements(r.nodes) AS node
              WHERE node->>'name' = %s
          )
        ORDER BY r.created_at DESC, r.id ASC
        LIMIT 1
        """,
        (node_name, username, now, node_name),
    )
    if not rows:
        return None
    try:
        port = int(rows[0]["port"])
    except (TypeError, ValueError):
        return None
    token = rows[0]["vm_password_encrypted"]
    if not isinstance(token, str) or token == "":
        return None
    return str(rows[0]["id"]), port, token, float(rows[0]["expires_at"])


def active_reservation_uses_node(conn, name: str) -> bool:
    """True when an active reservation still lists this node. Non-arrays do not match."""
    row = conn.execute(
        """
        SELECT 1
        FROM reservations AS r
        WHERE r.status = 'active'
          AND jsonb_typeof(COALESCE(r.nodes, '[]'::jsonb)) = 'array'
          AND EXISTS (
              SELECT 1
              FROM jsonb_array_elements(r.nodes) AS node
              WHERE node->>'name' = %s
          )
        LIMIT 1
        """,
        (name,),
    ).fetchone()
    return row is not None


def next_reservation_expiry() -> float | None:
    rows = fetch_all(
        """
        SELECT MIN(expires_at) AS deadline
        FROM reservations
        WHERE status = 'active' AND expires_at > 0
        """
    )
    deadline = rows[0]["deadline"] if rows else None
    if deadline is None:
        return None
    return float(deadline)


def public_reservation(row, username: str):
    """Reservation fields safe to return. No machine password."""
    return {
        "id": row["id"],
        "username": username,
        "vm_count": int(row["vm_count"]),
        "duration_minutes": int(row["duration_minutes"]),
        "status": row["status"],
        "created_at": float(row["created_at"]),
        "expires_at": float(row["expires_at"]),
        "nodes": row["nodes"] if row["nodes"] is not None else [],
        "final_stats": row["final_stats"] if row["final_stats"] is not None else {},
        "packages": row["packages"] if row["packages"] is not None else [],
    }


def list_user_reservations(username: str):
    """All reservations for one user. The machine password is not selected."""
    rows = fetch_all(
        """
        SELECT r.id, r.vm_count, r.duration_minutes, r.status,
               r.created_at, r.expires_at, r.nodes, r.final_stats, r.packages
        FROM reservations AS r
        JOIN users AS u ON r.user_id = u.id
        WHERE u.username = %s
        ORDER BY r.created_at DESC, r.id ASC
        """,
        (username,),
    )
    return [public_reservation(row, username) for row in rows]


def count_active_reservations() -> int:
    """Reservations whose stored status is active. The clock is not consulted."""
    rows = fetch_all(
        """
        SELECT COUNT(*) AS active_reservations
        FROM reservations
        WHERE status = 'active'
        """,
    )
    return int(rows[0]["active_reservations"])


def list_all_reservations():
    """Every reservation. The machine password is not selected."""
    rows = fetch_all(
        """
        SELECT r.id, u.username, r.vm_count, r.duration_minutes, r.status,
               r.created_at, r.expires_at, r.nodes, r.final_stats, r.packages
        FROM reservations AS r
        JOIN users AS u ON r.user_id = u.id
        ORDER BY r.created_at DESC, r.id ASC
        """,
    )
    return [public_reservation(row, row["username"]) for row in rows]


def get_reservation(reservation_id: str):
    """One reservation by id. None when it does not exist. No machine password."""
    rows = fetch_all(
        """
        SELECT r.id, u.username, r.vm_count, r.duration_minutes, r.status,
               r.created_at, r.expires_at, r.nodes, r.final_stats, r.packages
        FROM reservations AS r
        JOIN users AS u ON r.user_id = u.id
        WHERE r.id = %s
        """,
        (reservation_id,),
    )
    if not rows:
        return None
    row = rows[0]
    return public_reservation(row, row["username"])


def insert_reservation(
    username: str,
    vm_count: int,
    duration_minutes: int,
    expires_at: float,
    nodes: list[dict],
    packages: list[str],
    encrypted_password: str,
) -> str | None:
    """Insert one active reservation. None when the user row does not exist."""
    reservation_id = str(uuid.uuid4())
    created_at = time.time()
    committed = False
    missing_user = False
    try:
        with connect() as conn:
            user = conn.execute(
                "SELECT id FROM users WHERE username = %s",
                (username,),
            ).fetchone()
            if user is None:
                conn.rollback()
                missing_user = True
            else:
                conn.execute(
                    """
                    INSERT INTO reservations (
                        id, user_id, vm_count, duration_minutes, status,
                        created_at, expires_at, nodes, final_stats, packages,
                        vm_password_encrypted
                    ) VALUES (
                        %s, %s, %s, %s, 'active',
                        %s, %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        reservation_id,
                        user["id"],
                        vm_count,
                        duration_minutes,
                        created_at,
                        expires_at,
                        Json(nodes),
                        Json({}),
                        Json(packages),
                        encrypted_password,
                    ),
                )
                conn.commit()
                committed = True
    except Exception as exc:
        if committed:
            logger.exception(
                "reservation %s was saved but the database connection failed while closing",
                reservation_id,
            )
            return reservation_id
        if missing_user and isinstance(exc, (psycopg.OperationalError, psycopg.InterfaceError)):
            return None
        if isinstance(exc, (psycopg.OperationalError, psycopg.InterfaceError)):
            raise DatabaseUnavailable from exc
        raise
    if missing_user:
        return None
    return reservation_id
