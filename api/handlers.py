import logging

from fastapi import FastAPI, Request

from api.errors import (
    AccountMissing,
    AdminCannotReserve,
    BadProvision,
    ContainerConfigError,
    DatabaseUnavailable,
    EncryptionUnavailable,
    FieldTooLong,
    MachinePasswordRejected,
    NotEnoughNodes,
    PackageRejected,
    PoolRecoverError,
    ReservationMissing,
    ReservationNotActive,
    UsernameNotProvisionable,
    UsernameReserved,
    UsernameTaken,
)
from api.responses import (
    ADMIN_CANNOT_RESERVE,
    AUTH_REQUIRED,
    BAD_PROVISION,
    CONTAINER_CONFIG_FAILED,
    DATABASE_UNAVAILABLE,
    ENCRYPTION_UNAVAILABLE,
    FIELD_TOO_LONG,
    MACHINE_PASSWORD_REJECTED,
    PACKAGE_REJECTED,
    POOL_RECOVER_FAILED,
    RESERVATION_NOT_ACTIVE,
    RESERVATION_NOT_FOUND,
    USERNAME_NOT_PROVISIONABLE,
    USERNAME_TAKEN,
    error_response,
    not_enough_nodes_message,
    username_reserved_message,
)

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DatabaseUnavailable)
    def database_unavailable(_request: Request, exc: DatabaseUnavailable):
        logger.error("database read failed", exc_info=exc)
        return error_response(DATABASE_UNAVAILABLE, 503)

    @app.exception_handler(UsernameReserved)
    def username_reserved(_request: Request, exc: UsernameReserved):
        return error_response(username_reserved_message(exc.username), 400)

    @app.exception_handler(UsernameTaken)
    def username_taken(_request: Request, exc: UsernameTaken):
        return error_response(USERNAME_TAKEN, 409)

    @app.exception_handler(FieldTooLong)
    def field_too_long(_request: Request, exc: FieldTooLong):
        return error_response(FIELD_TOO_LONG, 400)

    @app.exception_handler(NotEnoughNodes)
    def not_enough_nodes(_request: Request, exc: NotEnoughNodes):
        return error_response(
            not_enough_nodes_message(exc.requested, exc.free),
            409,
        )

    @app.exception_handler(ContainerConfigError)
    def container_config_failed(_request: Request, exc: ContainerConfigError):
        logger.error("container configuration failed", exc_info=exc)
        return error_response(CONTAINER_CONFIG_FAILED, 503)

    @app.exception_handler(BadProvision)
    def bad_provision(_request: Request, exc: BadProvision):
        return error_response(BAD_PROVISION, 400)

    @app.exception_handler(MachinePasswordRejected)
    def machine_password_rejected(_request: Request, exc: MachinePasswordRejected):
        return error_response(MACHINE_PASSWORD_REJECTED, 400)

    @app.exception_handler(UsernameNotProvisionable)
    def username_not_provisionable(_request: Request, exc: UsernameNotProvisionable):
        return error_response(USERNAME_NOT_PROVISIONABLE, 400)

    @app.exception_handler(PackageRejected)
    def package_rejected(_request: Request, exc: PackageRejected):
        return error_response(PACKAGE_REJECTED, 400)

    @app.exception_handler(EncryptionUnavailable)
    def encryption_unavailable(_request: Request, exc: EncryptionUnavailable):
        logger.error("machine password encryption failed", exc_info=exc)
        return error_response(ENCRYPTION_UNAVAILABLE, 503)

    @app.exception_handler(AdminCannotReserve)
    def admin_cannot_reserve(_request: Request, exc: AdminCannotReserve):
        return error_response(ADMIN_CANNOT_RESERVE, 403)

    @app.exception_handler(AccountMissing)
    def account_missing(_request: Request, exc: AccountMissing):
        return error_response(AUTH_REQUIRED, 401)

    @app.exception_handler(ReservationMissing)
    def reservation_missing(_request: Request, exc: ReservationMissing):
        return error_response(RESERVATION_NOT_FOUND, 404)

    @app.exception_handler(ReservationNotActive)
    def reservation_not_active(_request: Request, exc: ReservationNotActive):
        return error_response(RESERVATION_NOT_ACTIVE, 409)

    @app.exception_handler(PoolRecoverError)
    def pool_recover_failed(_request: Request, exc: PoolRecoverError):
        logger.error("pool recovery failed", exc_info=exc)
        return error_response(POOL_RECOVER_FAILED, 503)
