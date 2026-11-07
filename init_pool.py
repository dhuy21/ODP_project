"""Create the 30 SSH containers and store them as free PostgreSQL pool nodes.

Run from the repository root with the API virtualenv:

    api/.venv/bin/python init_pool.py
"""

import platform
import sys
from pathlib import Path

import docker
from docker.errors import NotFound

from api.errors import DatabaseUnavailable
from api.pool_sql import delete_pool_node, save_free_node

ROOT = Path(__file__).resolve().parent
POOL_SIZE = 30
NETWORK = "pool-network"
SUBNET = "172.30.0.0/24"


def main() -> None:
    print("Starting ODP pool initialization...")
    try:
        client = docker.from_env()
        client.ping()
    except Exception:
        print("Error: Cannot connect to Docker. Is it running?")
        sys.exit(1)
    if not _ensure_network(client) or not _build_image(client):
        sys.exit(1)
    failed = 0
    for index in range(1, POOL_SIZE + 1):
        if not _start_node(client, index):
            failed += 1
    if failed:
        print(f"Initialization failed for {failed} containers.")
        sys.exit(1)
    print(f"Pool initialized with {POOL_SIZE} free nodes.")


def _ensure_network(client) -> bool:
    try:
        client.networks.get(NETWORK)
    except NotFound:
        try:
            ipam_pool = docker.types.IPAMPool(subnet=SUBNET)
            ipam = docker.types.IPAMConfig(pool_configs=[ipam_pool])
            client.networks.create(NETWORK, driver="bridge", ipam=ipam)
        except Exception as exc:
            print(f"Could not create {NETWORK}: {exc}")
            return False
        print(f"Created network {NETWORK}")
    except Exception as exc:
        print(f"Could not read {NETWORK}: {exc}")
        return False
    return True


def _build_image(client) -> bool:
    arch = platform.machine()
    docker_platform = "linux/arm64" if arch in ("aarch64", "arm64") else "linux/amd64"
    print(f"Building pool-node:latest for {docker_platform}...")
    try:
        client.images.build(
            path=str(ROOT / "Docker" / "ssh"),
            dockerfile="dockerfile",
            tag="pool-node:latest",
            platform=docker_platform,
            rm=True,
        )
    except Exception as exc:
        print(f"Image build failed: {exc}")
        return False
    return True


def _start_node(client, index: int) -> bool:
    name = f"pool-node-{index}"
    port = 2999 + index
    try:
        old = client.containers.get(name)
        old.remove(force=True)
    except NotFound:
        pass
    except Exception as exc:
        print(f"Failed to replace {name}: {exc}")
        return False
    try:
        container = client.containers.run(
            "pool-node:latest",
            name=name,
            detach=True,
            network=NETWORK,
            ports={"22/tcp": port},
            restart_policy={"Name": "unless-stopped"},
        )
    except Exception as exc:
        print(f"Failed to start {name}: {exc}")
        _remove_named(client, name)
        _clear_row(name)
        return False
    try:
        container.reload()
        ip = container.attrs["NetworkSettings"]["Networks"][NETWORK]["IPAddress"]
        if not isinstance(ip, str) or ip == "":
            print(f"Failed to start {name}: Docker did not assign an address")
            _remove_container(container)
            _clear_row(name)
            return False
        save_free_node(name, ip, port)
    except DatabaseUnavailable:
        print(f"Failed to save {name}: database unavailable")
        _remove_container(container)
        _clear_row(name)
        return False
    except Exception as exc:
        print(f"Failed to start {name}: {exc}")
        _remove_container(container)
        _clear_row(name)
        return False
    print(f"Started {name} at {ip}:{port}")
    return True


def _clear_row(name: str) -> None:
    try:
        delete_pool_node(name)
    except DatabaseUnavailable:
        print(f"Failed to clear {name}: database unavailable")


def _remove_named(client, name: str) -> None:
    try:
        _remove_container(client.containers.get(name))
    except NotFound:
        pass
    except Exception as exc:
        print(f"Could not remove {name}: {exc}")


def _remove_container(container) -> None:
    try:
        container.remove(force=True)
    except Exception as exc:
        print(f"Could not remove {container.name}: {exc}")


if __name__ == "__main__":
    main()
