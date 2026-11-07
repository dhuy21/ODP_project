"""SQL for pool_nodes. Callers own the transaction, except the helpers that open one."""

import logging

import psycopg

from api.db import connect, fetch_all
from api.errors import DatabaseUnavailable, NotEnoughNodes

logger = logging.getLogger(__name__)


def free_owned_nodes(conn, names: list[str], owner: str) -> None:
    """Free these nodes only while this owner still holds them."""
    if not names:
        return
    conn.execute(
        """
        UPDATE pool_nodes
        SET status = 'free', owner = NULL, expiry = 0
        WHERE name = ANY(%s) AND owner = %s
        """,
        (names, owner),
    )


def lock_pool_node(conn, name: str):
    return conn.execute(
        """
        SELECT owner, status, expiry
        FROM pool_nodes
        WHERE name = %s
        FOR UPDATE
        """,
        (name,),
    ).fetchone()


def free_allocated_node(conn, name: str) -> None:
    conn.execute(
        """
        UPDATE pool_nodes
        SET status = 'free', owner = NULL, expiry = 0
        WHERE name = %s AND status = 'allocated'
        """,
        (name,),
    )


def list_expired_allocated_names(now: float) -> list[str]:
    rows = fetch_all(
        """
        SELECT name
        FROM pool_nodes
        WHERE status = 'allocated' AND expiry > 0 AND expiry < %s
        ORDER BY name ASC
        """,
        (now,),
    )
    return [row["name"] for row in rows]


def next_node_expiry() -> float | None:
    rows = fetch_all(
        """
        SELECT MIN(expiry) AS deadline
        FROM pool_nodes
        WHERE status = 'allocated' AND expiry > 0
        """
    )
    deadline = rows[0]["deadline"] if rows else None
    if deadline is None:
        return None
    return float(deadline)


def get_pool_status():
    """Same counts as the Flask pool status: total plus free and allocated."""
    rows = fetch_all("SELECT status, COUNT(*) AS count FROM pool_nodes GROUP BY status")
    stats = {"total": 0, "free": 0, "allocated": 0}
    for row in rows:
        count = int(row["count"])
        stats["total"] += count
        if row["status"] in ("free", "allocated"):
            stats[row["status"]] = count
    return stats


def list_pool_nodes():
    """Pool rows from SQL only: name, ip, port, status, owner, expiry."""
    rows = fetch_all(
        """
        SELECT name, ip, port, status, owner, expiry
        FROM pool_nodes
        ORDER BY port ASC, name ASC
        """
    )
    return [
        {
            "name": row["name"],
            "ip": row["ip"],
            "port": int(row["port"]),
            "status": row["status"],
            "owner": row["owner"],
            "expiry": float(row["expiry"]),
        }
        for row in rows
    ]


def take_free_nodes(count: int, username: str, expiry: float):
    """Lock and mark free nodes allocated. NotEnoughNodes when the pool is short."""
    committed = False
    rows = []
    shortage = None
    try:
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT name, ip, port
                FROM pool_nodes
                WHERE status = 'free'
                ORDER BY port ASC, name ASC
                LIMIT %s
                FOR UPDATE SKIP LOCKED
                """,
                (count,),
            ).fetchall()
            if len(rows) < count:
                shortage = NotEnoughNodes(count, len(rows))
                conn.rollback()
            else:
                names = [row["name"] for row in rows]
                conn.execute(
                    """
                    UPDATE pool_nodes
                    SET status = 'allocated', owner = %s, expiry = %s
                    WHERE name = ANY(%s)
                    """,
                    (username, expiry, names),
                )
                conn.commit()
                committed = True
    except (psycopg.OperationalError, psycopg.InterfaceError) as exc:
        if committed:
            logger.exception("nodes were allocated but the database connection failed while closing")
        elif shortage is not None:
            raise shortage from exc
        else:
            raise DatabaseUnavailable from exc
    if shortage is not None:
        raise shortage
    return [{"name": row["name"], "ip": row["ip"], "port": int(row["port"])} for row in rows]


def save_free_node(name: str, ip: str, port: int) -> None:
    """Store one pool container as free. An existing row is reset to free."""
    committed = False
    try:
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO pool_nodes (name, ip, port, status, owner, expiry)
                VALUES (%s, %s, %s, 'free', NULL, 0)
                ON CONFLICT (name) DO UPDATE
                SET ip = EXCLUDED.ip,
                    port = EXCLUDED.port,
                    status = 'free',
                    owner = NULL,
                    expiry = 0
                """,
                (name, ip, port),
            )
            conn.commit()
            committed = True
    except (psycopg.OperationalError, psycopg.InterfaceError) as exc:
        if committed:
            logger.exception("the node was saved but the database connection failed while closing")
            return
        raise DatabaseUnavailable from exc


def free_nodes(names: list[str], owner: str) -> None:
    """Return this owner's nodes to the pool. Nodes owned by someone else stay put."""
    if not names:
        return
    committed = False
    try:
        with connect() as conn:
            free_owned_nodes(conn, names, owner)
            conn.commit()
            committed = True
    except (psycopg.OperationalError, psycopg.InterfaceError) as exc:
        if committed:
            logger.exception("nodes were freed but the database connection failed while closing")
            return
        raise DatabaseUnavailable from exc
