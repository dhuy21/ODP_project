"""Who may open a terminal. The machine password stays on the server."""

from api.reservation_sql import find_active_terminal_reservation

TERMINAL_UNAUTHORIZED = "Unauthorized"
TERMINAL_NODE_REQUIRED = "Node name is required"
TERMINAL_NO_RESERVATION = "No active reservation found for this container"


def reservation_info(socket_username: str, requested_username, node_name, now: float) -> dict:
    """Facts for one node. Never includes the machine password."""
    if requested_username != socket_username:
        return {"error": TERMINAL_UNAUTHORIZED}
    if not isinstance(node_name, str) or node_name == "":
        return {"error": TERMINAL_NODE_REQUIRED}
    reservation_id = find_active_terminal_reservation(socket_username, node_name, now)
    if reservation_id is None:
        return {"error": TERMINAL_NO_RESERVATION}
    return {
        "reservation_id": reservation_id,
        "username": socket_username,
        "node_name": node_name,
    }
