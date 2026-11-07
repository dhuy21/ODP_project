import base64
import logging
import time

from api.errors import ContainerConfigError, PoolRecoverError

logger = logging.getLogger(__name__)


def configure_container(name: str, username: str, password: str) -> None:
    """Create the account inside one pool container. Arguments stay out of the shell."""
    try:
        import docker

        client = docker.from_env()
    except Exception as exc:
        raise ContainerConfigError(name) from exc
    try:
        try:
            container = client.containers.get(name)
        except Exception as exc:
            raise ContainerConfigError(name) from exc
        exists = container.exec_run(["id", "-u", "--", username])
        if exists.exit_code != 0:
            created = container.exec_run(["useradd", "-m", "-s", "/bin/bash", "--", username])
            if created.exit_code != 0:
                raise ContainerConfigError(name)
        secret = base64_password_line(username, password)
        changed = container.exec_run(
            ["sh", "-c", 'printf "%s" "$1" | base64 -d | chpasswd', "sh", secret]
        )
        if changed.exit_code != 0:
            raise ContainerConfigError(name)
        sudo = container.exec_run(["usermod", "-aG", "sudo", "--", username])
        if sudo.exit_code != 0:
            raise ContainerConfigError(name)
    except ContainerConfigError:
        raise
    except Exception as exc:
        raise ContainerConfigError(name) from exc
    finally:
        try:
            client.close()
        except Exception:
            logger.exception("could not close the docker client for %s", name)


def remove_container_user(name: str, username: str) -> None:
    """Remove an account left behind by a failed provision. Never raises."""
    import docker

    try:
        client = docker.from_env()
        try:
            container = client.containers.get(name)
            container.exec_run(["pkill", "-9", "-u", username])
            time.sleep(0.5)
            container.exec_run(["userdel", "-r", "-f", "--", username])
        finally:
            client.close()
    except docker.errors.NotFound:
        logger.warning("container %s is already gone", name)
    except Exception:
        logger.exception("could not remove the account from %s", name)


def restart_stopped_pool_containers() -> int:
    """Start stopped pool-node containers. Missing containers are not created."""
    try:
        import docker

        client = docker.from_env()
    except Exception as exc:
        raise PoolRecoverError() from exc
    try:
        started = 0
        for container in client.containers.list(all=True, filters={"name": "pool-node-"}):
            if container.status == "running" or not container.name.startswith("pool-node-"):
                continue
            container.start()
            started += 1
        return started
    except Exception as exc:
        raise PoolRecoverError() from exc
    finally:
        try:
            client.close()
        except Exception:
            logger.exception("could not close the docker client after pool recovery")


def base64_password_line(username: str, password: str) -> str:
    return base64.b64encode(f"{username}:{password}\n".encode()).decode("ascii")
