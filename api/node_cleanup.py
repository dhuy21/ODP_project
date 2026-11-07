"""Remove Linux accounts and free the matching pool nodes."""

from api.containers import remove_container_user
from api.pool_sql import free_nodes, free_owned_nodes


def detach_nodes(conn, username: str, names: list[str]) -> None:
    for name in names:
        remove_container_user(name, username)
    free_owned_nodes(conn, names, username)


def release_owned_nodes(names: list[str], username: str) -> None:
    """Container cleanup, then a separate transaction that frees this owner's nodes."""
    for name in names:
        remove_container_user(name, username)
    free_nodes(names, username)
