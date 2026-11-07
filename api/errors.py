class DatabaseUnavailable(Exception):
    """PostgreSQL cannot be reached. The HTTP layer turns this into a 503."""


class UsernameReserved(Exception):
    def __init__(self, username: str):
        self.username = username


class UsernameTaken(Exception):
    """The username already exists."""


class FieldTooLong(Exception):
    """Username or email does not fit the column."""


class NotEnoughNodes(Exception):
    """The pool does not have enough free containers."""

    def __init__(self, requested: int, free: int):
        self.requested = requested
        self.free = free


class ContainerConfigError(Exception):
    """A container could not be prepared for the reservation."""


class BadProvision(Exception):
    """vm_count, duration, or the machine password is not usable."""


class MachinePasswordRejected(Exception):
    """The machine password would break chpasswd or the encrypted column."""


class UsernameNotProvisionable(Exception):
    """The account name is not safe to create inside a container."""


class PackageRejected(Exception):
    """A package name would break the Ansible inventory line."""


class EncryptionUnavailable(Exception):
    """The Fernet key cannot encrypt a machine password."""


class AdminCannotReserve(Exception):
    """The database role is admin, so this account cannot provision."""


class AccountMissing(Exception):
    """The session username has no row in users."""


class ReservationMissing(Exception):
    """No reservation with this id belongs to the session user."""


class ReservationNotActive(Exception):
    """The reservation exists but is not active, so its nodes must stay untouched."""


class PoolRecoverError(Exception):
    """Stopped pool containers could not be restarted."""
