import logging

import psycopg

from api.db import connect
from api.errors import DatabaseUnavailable, ReservationMissing, ReservationNotActive
from api.node_cleanup import detach_nodes
from api.reservation_sql import (
    lock_active_reservations,
    lock_owned_reservation,
    lock_reservation,
    mark_deleted,
    mark_if_active,
    node_names,
)
from api.user_sql import delete_user_row, lock_user

logger = logging.getLogger(__name__)


def release_reservation(username: str, reservation_id: str) -> None:
    """Free one active reservation. Other people's nodes and inactive rows stay put."""
    committed = False
    missing = False
    inactive = False
    try:
        with connect() as conn:
            row = lock_owned_reservation(conn, reservation_id, username)
            if row is None:
                conn.rollback()
                missing = True
            elif row["status"] != "active":
                conn.rollback()
                inactive = True
            else:
                detach_nodes(conn, username, node_names(row["nodes"]))
                mark_if_active(conn, reservation_id, "released")
                conn.commit()
                committed = True
    except (psycopg.OperationalError, psycopg.InterfaceError) as exc:
        if committed:
            logger.exception(
                "reservation %s was released but the database connection failed while closing",
                reservation_id,
            )
            return
        if missing:
            raise ReservationMissing() from exc
        if inactive:
            raise ReservationNotActive() from exc
        raise DatabaseUnavailable from exc
    if missing:
        raise ReservationMissing()
    if inactive:
        raise ReservationNotActive()


def delete_reservation(reservation_id: str) -> None:
    """Free this reservation's nodes, then mark the row deleted. Any owner."""
    committed = False
    missing = False
    try:
        with connect() as conn:
            row = lock_reservation(conn, reservation_id)
            if row is None:
                conn.rollback()
                missing = True
            else:
                detach_nodes(conn, row["username"], node_names(row["nodes"]))
                mark_deleted(conn, reservation_id)
                conn.commit()
                committed = True
    except (psycopg.OperationalError, psycopg.InterfaceError) as exc:
        if committed:
            logger.exception(
                "reservation %s was deleted but the database connection failed while closing",
                reservation_id,
            )
            return
        if missing:
            raise ReservationMissing() from exc
        raise DatabaseUnavailable from exc
    if missing:
        raise ReservationMissing()


def delete_account(username: str) -> tuple[str, int, int]:
    """Delete a normal user after freeing their active nodes.

    Returns missing, admin, or deleted, plus node and reservation counts.
    """
    committed = False
    outcome = "deleted"
    node_count = 0
    reservation_count = 0
    try:
        with connect() as conn:
            user = lock_user(conn, username)
            if user is None:
                conn.rollback()
                outcome = "missing"
            elif str(user["role"]) == "admin":
                conn.rollback()
                outcome = "admin"
            else:
                reservations = lock_active_reservations(conn, user["id"])
                reservation_count = len(reservations)
                for reservation in reservations:
                    names = node_names(reservation["nodes"])
                    node_count += len(names)
                    detach_nodes(conn, username, names)
                delete_user_row(conn, user["id"])
                conn.commit()
                committed = True
    except (psycopg.OperationalError, psycopg.InterfaceError) as exc:
        if committed:
            logger.exception(
                "user %s was deleted but the database connection failed while closing",
                username,
            )
            return "deleted", node_count, reservation_count
        if outcome == "missing":
            return "missing", 0, 0
        if outcome == "admin":
            return "admin", 0, 0
        raise DatabaseUnavailable from exc
    return outcome, node_count, reservation_count
