from fastapi.responses import JSONResponse

DATABASE_UNAVAILABLE = "Database unavailable"
RESERVATION_NOT_FOUND = "Reservation not found"
USERNAME_TAKEN = "Username already exists"
FIELD_TOO_LONG = "Username or email is too long"
INVALID_CREDENTIALS = "Invalid credentials"
AUTH_REQUIRED = "Authentication required"
ADMIN_REQUIRED = "Admin access required"
INVALID_ROLE = "Invalid role"
SYSTEM_ADMIN_ROLE = "Cannot change system admin role"
USER_NOT_FOUND = "User not found"
CANNOT_DEMOTE_ADMIN = (
    "Cannot demote admin users. Only regular users can have their roles changed."
)
CANNOT_DELETE_SYSTEM_ADMIN = "Cannot delete the system admin account"
CANNOT_DELETE_ADMIN = "Cannot delete admin users. Only regular users can be deleted."
ADMIN_CANNOT_RESERVE = (
    "Admin users cannot create reservations. Please use the admin panel to manage resources."
)


def not_enough_nodes_message(requested: int, free: int) -> str:
    return f"Not enough containers available. You need {requested} but only {free} are free."


CONTAINER_CONFIG_FAILED = "Could not configure a container"
POOL_RECOVER_FAILED = "Could not restart the pool containers"
BAD_PROVISION = "vm_count and duration must be positive, and a machine password is required"
MACHINE_PASSWORD_REJECTED = "Machine password contains a line break or is too long"
USERNAME_NOT_PROVISIONABLE = "Username cannot be used inside a container"
PACKAGE_REJECTED = "A package name is not usable"
ENCRYPTION_UNAVAILABLE = "Password encryption is unavailable"
RESERVATION_NOT_ACTIVE = "Reservation is not active"
RESERVATION_DELETED = "Reservation deleted"
RESOURCES_RELEASED = "Resources released"


def username_reserved_message(username: str) -> str:
    return f'Username "{username}" is reserved and cannot be used. Please choose another username.'


def error_response(message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"status": "error", "message": message},
    )
