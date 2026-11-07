import json
import logging
import os
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

PLAYBOOK = Path(__file__).resolve().parents[1] / "Ansible" / "playbook.yml"
INVENTORY_DIR = PLAYBOOK.parent


def schedule_package_install(
    username: str,
    nodes: list[dict],
    password: str,
    packages: list[str],
    reservation_id: str,
) -> None:
    if not packages:
        return
    thread = threading.Thread(
        target=_install,
        args=(username, nodes, password, packages, reservation_id),
        daemon=True,
    )
    try:
        thread.start()
    except Exception:
        logger.exception(
            "failed to start package install for reservation %s",
            reservation_id,
        )


def _install(
    username: str,
    nodes: list[dict],
    password: str,
    packages: list[str],
    reservation_id: str,
) -> None:
    import subprocess

    inventory = _inventory_path(reservation_id)
    if inventory is None:
        return
    try:
        _write_private(inventory, _inventory_yaml(username, nodes, password, packages))
        completed = subprocess.run(
            ["ansible-playbook", "-i", str(inventory), str(PLAYBOOK)],
            cwd=PLAYBOOK.parent.parent,
            timeout=900,
            check=False,
        )
        if completed.returncode != 0:
            logger.error(
                "package install for reservation %s failed with status %s",
                reservation_id,
                completed.returncode,
            )
    finally:
        inventory.unlink(missing_ok=True)


def _inventory_path(reservation_id: str) -> Path | None:
    """Stay inside the Ansible directory. A reservation id must not change the folder."""
    root = INVENTORY_DIR.resolve()
    path = (INVENTORY_DIR / f"inventory_{reservation_id}.yml").resolve()
    if path.parent != root:
        logger.error("refusing an inventory path outside the Ansible directory")
        return None
    return path


def _inventory_yaml(
    username: str,
    nodes: list[dict],
    password: str,
    packages: list[str],
) -> str:
    """YAML inventory. Quoted strings keep passwords and names such as on/yes intact."""
    lines = [f"{_yaml_string(username)}:", "  hosts:"]
    for node in nodes:
        lines.append(f"    {_yaml_string(str(node['name']))}:")
        lines.append("      ansible_host: 127.0.0.1")
        lines.append(f"      ansible_port: {int(node['port'])}")
        lines.append(f"      ansible_user: {_yaml_string(username)}")
        quoted = _yaml_string(password)
        lines.append(f"      ansible_ssh_pass: {quoted}")
        lines.append(f"      ansible_become_pass: {quoted}")
    lines.append("  vars:")
    lines.append(
        "    ansible_ssh_common_args: "
        + _yaml_string("-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null")
    )
    lines.append(f"    packages: {_yaml_string(','.join(packages))}")
    return "\n".join(lines) + "\n"


def _yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _write_private(path: Path, text: str) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)
    path.chmod(0o600)
