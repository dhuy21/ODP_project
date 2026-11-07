"""PostgreSQL connection. Table queries live in user_sql, pool_sql, and reservation_sql."""

import logging

import psycopg
from psycopg.rows import dict_row

from api.errors import DatabaseUnavailable
from api.settings import get_settings

logger = logging.getLogger(__name__)


def connect():
    settings = get_settings()
    return psycopg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        user=settings.postgres_user,
        password=settings.postgres_password,
        dbname=settings.postgres_db,
        row_factory=dict_row,
    )


def fetch_all(query, params=None):
    """Run one read query. Connection failures become DatabaseUnavailable."""
    fetched = False
    rows = []
    try:
        with connect() as conn:
            rows = conn.execute(query, params).fetchall()
            fetched = True
    except (psycopg.OperationalError, psycopg.InterfaceError) as exc:
        if fetched:
            logger.exception("the query finished but the database connection failed while closing")
            return rows
        raise DatabaseUnavailable from exc
    return rows
