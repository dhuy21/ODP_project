import logging
import re
import time

from api.ansible_jobs import schedule_package_install
from api.containers import configure_container
from api.errors import (
    AccountMissing,
    AdminCannotReserve,
    BadProvision,
    EncryptionUnavailable,
    MachinePasswordRejected,
    PackageRejected,
    UsernameNotProvisionable,
)
from api.machine_passwords import encrypt_machine_password
from api.node_cleanup import release_owned_nodes
from api.pool_sql import take_free_nodes
from api.reservation_sql import insert_reservation
from api.user_sql import find_user_role
from api.usernames import RESERVED_USERNAMES

logger = logging.getLogger(__name__)

_USERNAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]{0,31}$")
_PACKAGE = re.compile(r"^[a-z0-9][a-z0-9+.-]*$")
_INT_MAX = 2_147_483_647
_PASSWORD_MAX_BYTES = 127


def provision_machines(
    username: str,
    vm_count: int,
    duration: int,
    password: str,
    packages: str,
) -> dict:
    if vm_count < 1 or duration < 1 or vm_count > _INT_MAX or duration > _INT_MAX or not password:
        raise BadProvision()
    if "\x00" in password or "\n" in password or "\r" in password:
        raise MachinePasswordRejected()
    if len(password.encode()) > _PASSWORD_MAX_BYTES:
        raise MachinePasswordRejected()
    try:
        encrypted = encrypt_machine_password(password)
    except Exception as exc:
        raise EncryptionUnavailable() from exc
    if len(encrypted) > 255:
        raise MachinePasswordRejected()
    if _USERNAME.fullmatch(username) is None:
        raise UsernameNotProvisionable()
    package_list = [item.strip() for item in packages.split(",") if item.strip()]
    if any(_PACKAGE.fullmatch(item) is None for item in package_list):
        raise PackageRejected()
    role = find_user_role(username)
    if role is None:
        raise AccountMissing()
    if role == "admin":
        raise AdminCannotReserve()
    if username.lower() in RESERVED_USERNAMES:
        raise UsernameNotProvisionable()
    expires_at = time.time() + (duration * 60)
    nodes = take_free_nodes(vm_count, username, expires_at)
    names = [node["name"] for node in nodes]
    try:
        for node in nodes:
            configure_container(node["name"], username, password)
        reservation_id = insert_reservation(
            username=username,
            vm_count=vm_count,
            duration_minutes=duration,
            expires_at=expires_at,
            nodes=nodes,
            packages=package_list,
            encrypted_password=encrypted,
        )
    except Exception:
        logger.exception("provision failed after nodes were reserved")
        _release_attempt(names, username)
        raise
    if reservation_id is None:
        _release_attempt(names, username)
        raise AccountMissing()
    schedule_package_install(username, nodes, password, package_list, reservation_id)
    return {"reservation_id": reservation_id, "nodes": nodes}


def _release_attempt(names: list[str], username: str) -> None:
    try:
        release_owned_nodes(names, username)
    except Exception:
        logger.exception("failed to return nodes after a failed provision")
