from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

from api.auth import admin_denial, authenticate
from api.containers import restart_stopped_pool_containers
from api.expiry import start_expiry_thread, stop_expiry_thread
from api.handlers import register_exception_handlers
from api.pool_sql import get_pool_status, list_pool_nodes
from api.provisioning import provision_machines
from api.registration import register_user
from api.releasing import delete_account, delete_reservation, release_reservation
from api.reservation_sql import (
    count_active_reservations,
    get_reservation,
    list_all_reservations,
    list_user_reservations,
)
from api.responses import (
    ADMIN_CANNOT_RESERVE,
    AUTH_REQUIRED,
    CANNOT_DELETE_ADMIN,
    CANNOT_DELETE_SYSTEM_ADMIN,
    CANNOT_DEMOTE_ADMIN,
    INVALID_CREDENTIALS,
    INVALID_ROLE,
    RESERVATION_NOT_FOUND,
    RESERVATION_DELETED,
    RESOURCES_RELEASED,
    SYSTEM_ADMIN_ROLE,
    USER_NOT_FOUND,
    error_response,
)
from api.user_sql import (
    count_users_by_role,
    ensure_default_admin,
    find_user_role,
    list_users,
    set_user_role,
)
from api.settings import get_settings
from api.terminal_socket import close_user_terminals, wrap_fastapi


@asynccontextmanager
async def lifespan(_app: FastAPI):
    start_expiry_thread()
    try:
        yield
    finally:
        stop_expiry_thread()


app = FastAPI(title="ODP API", lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=get_settings().session_secret,
    same_site="lax",
    https_only=False,
)
register_exception_handlers(app)


class RegisterBody(BaseModel):
    username: str
    email: str
    password: str


class AdminCreateUserBody(BaseModel):
    username: str
    email: str
    password: str


class RoleBody(BaseModel):
    role: str


class LoginBody(BaseModel):
    username: str
    password: str


class ProvisionBody(BaseModel):
    vm_count: int
    duration: int = 60
    password: str
    packages: str = ""


@app.post("/provision")
def provision(body: ProvisionBody, request: Request):
    username = request.session.get("username")
    if not username:
        return error_response(AUTH_REQUIRED, 401)
    if request.session.get("role") == "admin":
        return error_response(ADMIN_CANNOT_RESERVE, 403)
    result = provision_machines(
        username,
        body.vm_count,
        body.duration,
        body.password,
        body.packages,
    )
    return {"status": "success", **result}


@app.post("/reservations/{reservation_id}/release")
def release(reservation_id: str, request: Request):
    username = request.session.get("username")
    if not username:
        return error_response(AUTH_REQUIRED, 401)
    release_reservation(username, reservation_id)
    return {"status": "success", "message": RESOURCES_RELEASED}


@app.post("/login")
def login(body: LoginBody, request: Request):
    ensure_default_admin()
    user = authenticate(body.username, body.password)
    if user is None:
        return error_response(INVALID_CREDENTIALS, 401)
    request.session.clear()
    request.session["username"] = user["username"]
    request.session["role"] = user["role"]
    return {"status": "success", "user": user["username"], "role": user["role"]}


@app.get("/session")
def current_session(request: Request):
    username = request.session.get("username")
    if not username:
        return error_response(AUTH_REQUIRED, 401)
    role = find_user_role(username)
    if role is None:
        request.session.clear()
        return error_response(AUTH_REQUIRED, 401)
    request.session["role"] = role
    return {"status": "success", "user": username, "role": role}


@app.post("/logout")
async def logout(request: Request):
    username = request.session.get("username")
    request.session.clear()
    if isinstance(username, str) and username != "":
        await close_user_terminals(username)
    return {"status": "success"}


@app.post("/register")
def register(body: RegisterBody):
    register_user(body.username, body.email, body.password)
    return {"status": "success", "message": "User registered successfully"}


@app.get("/admin/users")
def admin_users(request: Request):
    denied = admin_denial(request)
    if denied is not None:
        return denied
    return {"status": "success", "users": list_users()}


@app.get("/admin/reservations")
def admin_reservations(request: Request):
    denied = admin_denial(request)
    if denied is not None:
        return denied
    return {"status": "success", "reservations": list_all_reservations()}


@app.get("/admin/overview")
def admin_overview(request: Request):
    denied = admin_denial(request)
    if denied is not None:
        return denied
    accounts = count_users_by_role()
    pool = get_pool_status()
    return {
        "status": "success",
        "total_users": accounts["total_users"],
        "admin_count": accounts["admin_count"],
        "user_count": accounts["user_count"],
        "active_reservations": count_active_reservations(),
        "total_containers": pool["total"],
        "available_containers": pool["free"],
    }


@app.get("/admin/pool")
def admin_pool(request: Request):
    denied = admin_denial(request)
    if denied is not None:
        return denied
    return {"status": "success", "nodes": list_pool_nodes()}


@app.post("/admin/users")
def admin_create_user(body: AdminCreateUserBody, request: Request):
    denied = admin_denial(request)
    if denied is not None:
        return denied
    register_user(body.username, body.email, body.password)
    return {"status": "success", "message": "User registered successfully"}


@app.put("/admin/users/{username}/role")
def admin_update_role(username: str, body: RoleBody, request: Request):
    denied = admin_denial(request)
    if denied is not None:
        return denied
    if body.role not in ("user", "admin"):
        return error_response(INVALID_ROLE, 400)
    if username == "admin":
        return error_response(SYSTEM_ADMIN_ROLE, 400)
    outcome = set_user_role(username, body.role)
    if outcome == "missing":
        return error_response(USER_NOT_FOUND, 404)
    if outcome == "protected":
        return error_response(CANNOT_DEMOTE_ADMIN, 400)
    return {"status": "success", "message": f"Role updated to {body.role}"}


@app.delete("/admin/reservations/{reservation_id}")
def admin_delete_reservation(reservation_id: str, request: Request):
    denied = admin_denial(request)
    if denied is not None:
        return denied
    delete_reservation(reservation_id)
    return {"status": "success", "message": RESERVATION_DELETED}


@app.delete("/admin/users/{username}")
def admin_delete_user(username: str, request: Request):
    denied = admin_denial(request)
    if denied is not None:
        return denied
    if username == "admin":
        return error_response(CANNOT_DELETE_SYSTEM_ADMIN, 400)
    outcome, nodes, reservations = delete_account(username)
    if outcome == "missing":
        return error_response(USER_NOT_FOUND, 404)
    if outcome == "admin":
        return error_response(CANNOT_DELETE_ADMIN, 400)
    return {
        "status": "success",
        "message": (
            f"User {username} deleted. Released {nodes} containers and {reservations} reservations."
        ),
    }


@app.post("/admin/pool/recover")
def admin_recover_pool(request: Request):
    denied = admin_denial(request)
    if denied is not None:
        return denied
    restarted = restart_stopped_pool_containers()
    return {
        "status": "success",
        "message": "Pool recovery initiated",
        "restarted": restarted,
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/pool/status")
def pool_status():
    stats = get_pool_status()
    return {
        "status": "success",
        "total": stats["total"],
        "free": stats["free"],
        "allocated": stats["allocated"],
    }


@app.get("/pool/nodes")
def pool_nodes():
    return {"status": "success", "nodes": list_pool_nodes()}


@app.get("/users/{username}/reservations")
def user_reservations(username: str):
    return {"status": "success", "reservations": list_user_reservations(username)}


@app.get("/reservations/{reservation_id}")
def reservation_detail(reservation_id: str):
    reservation = get_reservation(reservation_id)
    if reservation is None:
        return error_response(RESERVATION_NOT_FOUND, 404)
    return {"status": "success", "reservation": reservation}


app = wrap_fastapi(app)
