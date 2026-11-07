"""SQL for the users table."""

import logging

import psycopg

from api.db import connect, fetch_all
from api.errors import DatabaseUnavailable, UsernameTaken
from api.passwords import hash_password

logger = logging.getLogger(__name__)


def find_user_credentials(username: str):
    """Username, password hash, and role. None when the user does not exist."""
    rows = fetch_all(
        """
        SELECT username, password_hash, role
        FROM users
        WHERE username = %s
        """,
        (username,),
    )
    if not rows:
        return None
    return rows[0]


def list_users():
    """Every account, without the password hash. Sorted by username."""
    rows = fetch_all(
        """
        SELECT u.username, u.email, u.role, u.created_at,
               COUNT(r.id) AS reservation_count
        FROM users AS u
        LEFT JOIN reservations AS r ON r.user_id = u.id
        GROUP BY u.id
        ORDER BY u.username ASC, u.id ASC
        """,
    )
    users = []
    for row in rows:
        created = row["created_at"]
        if hasattr(created, "isoformat"):
            created = created.isoformat()
        users.append(
            {
                "username": row["username"],
                "email": row["email"],
                "role": str(row["role"]),
                "created_at": created or "",
                "reservation_count": int(row["reservation_count"]),
            }
        )
    return users


def count_users_by_role():
    """How many accounts exist, split by role."""
    rows = fetch_all(
        """
        SELECT COUNT(*) AS total_users,
               COUNT(*) FILTER (WHERE role = 'admin') AS admin_count,
               COUNT(*) FILTER (WHERE role = 'user') AS user_count
        FROM users
        """,
    )
    row = rows[0]
    return {
        "total_users": int(row["total_users"]),
        "admin_count": int(row["admin_count"]),
        "user_count": int(row["user_count"]),
    }


def set_user_role(username: str, role: str) -> str:
    """updated, missing, or protected.

    An admin is not turned into a user. That decision uses the locked row.
    """
    committed = False
    outcome = ""
    try:
        with connect() as conn:
            row = lock_user(conn, username)
            if row is None:
                conn.rollback()
                outcome = "missing"
            elif str(row["role"]) == "admin" and role == "user":
                conn.rollback()
                outcome = "protected"
            else:
                conn.execute(
                    "UPDATE users SET role = %s WHERE id = %s",
                    (role, row["id"]),
                )
                conn.commit()
                committed = True
                outcome = "updated"
    except (psycopg.OperationalError, psycopg.InterfaceError) as exc:
        if committed:
            logger.exception(
                "role for %s was saved but the database connection failed while closing", username
            )
            return "updated"
        if outcome in ("missing", "protected"):
            return outcome
        raise DatabaseUnavailable from exc
    return outcome


def lock_user(conn, username: str):
    """Lock one account. None when the username does not exist."""
    return conn.execute(
        "SELECT id, role FROM users WHERE username = %s FOR UPDATE",
        (username,),
    ).fetchone()


def delete_user_row(conn, user_id: int) -> None:
    """Delete one account. Reservations disappear through the foreign key."""
    conn.execute("DELETE FROM users WHERE id = %s", (user_id,))


def find_user_role(username: str) -> str | None:
    """The account role. None when the username has no row."""
    rows = fetch_all("SELECT role FROM users WHERE username = %s", (username,))
    if not rows:
        return None
    return rows[0]["role"]


def ensure_default_admin() -> None:
    """Insert the default admin / admin account when that username is missing."""
    committed = False
    try:
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO users (username, email, password_hash, role)
                SELECT %s, %s, %s, 'admin'
                WHERE NOT EXISTS (
                    SELECT 1 FROM users WHERE username = 'admin'
                )
                """,
                ("admin", "admin@iac.com", hash_password("admin")),
            )
            conn.commit()
            committed = True
    except (psycopg.OperationalError, psycopg.InterfaceError) as exc:
        if committed:
            logger.exception(
                "the default admin was saved but the database connection failed while closing"
            )
            return
        raise DatabaseUnavailable from exc


def insert_user(username: str, email: str, password_hash: str) -> None:
    """Insert a normal user. A duplicate username becomes UsernameTaken."""
    committed = False
    duplicate = False
    try:
        with connect() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO users (username, email, password_hash, role)
                    VALUES (%s, %s, %s, 'user')
                    """,
                    (username, email, password_hash),
                )
                conn.commit()
                committed = True
            except psycopg.errors.UniqueViolation:
                duplicate = True
                conn.rollback()
    except (psycopg.OperationalError, psycopg.InterfaceError) as exc:
        if committed:
            logger.exception(
                "user %s was saved but the database connection failed while closing", username
            )
            return
        if duplicate:
            raise UsernameTaken() from exc
        raise DatabaseUnavailable from exc
    if duplicate:
        raise UsernameTaken()
