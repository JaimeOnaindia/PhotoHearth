import hashlib
import secrets
import time
from typing import Annotated

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select

from backend.db import connect, lock_auth
from backend.models import LoginAttempt, LoginSession, User

router = APIRouter(prefix="/api/auth", tags=["authentication"])
hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=1)
COOKIE = "photohearth_session"
# Equalize work when the owner has not been created yet.
DUMMY_HASH = hasher.hash(secrets.token_urlsafe(32))


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def session(request: Request) -> dict:
    token = request.cookies.get(COOKIE, "")
    with connect(request.app.state.settings) as db:
        row = db.get(LoginSession, digest(token))
        user = db.get(User, 1)
    if not row or row.expires <= int(time.time()) or not user:
        raise HTTPException(401, "Conecta con tu cuenta para continuar.")
    if request.method not in {"GET", "HEAD", "OPTIONS"} and not secrets.compare_digest(
        request.headers.get("x-csrf-token", ""), row.csrf
    ):
        raise HTTPException(403, "La sesión de seguridad no es válida. Recarga la página.")
    return {"name": user.name, "csrf": row.csrf}


class Login(BaseModel):
    password: str = Field(min_length=1, max_length=128)


def password_attempt(request: Request) -> User | None:
    settings = request.app.state.settings
    address = request.client.host if request.client else "unknown"
    now = int(time.time())
    with connect(settings) as db:
        lock_auth(db)
        db.execute(delete(LoginAttempt).where(LoginAttempt.attempted < now - 60))
        attempts = db.scalar(
            select(func.count())
            .select_from(LoginAttempt)
            .where(
                LoginAttempt.address == address,
            )
        )
        if attempts >= 5:
            raise HTTPException(
                429, "Demasiados intentos. Espera un minuto.", {"Retry-After": "60"}
            )
        db.add(LoginAttempt(address=address, attempted=now))
        owner = db.get(User, 1)
    return owner


@router.post("/login")
def login(body: Login, request: Request, response: Response):
    settings = request.app.state.settings
    owner = password_attempt(request)
    try:
        hasher.verify(owner.password_hash if owner else DUMMY_HASH, body.password)
        valid = owner is not None
    except (VerificationError, InvalidHashError):
        valid = False
    if not valid:
        raise HTTPException(401, "La contraseña no es correcta.")
    token, csrf = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
    now = int(time.time())
    with connect(settings) as db:
        lock_auth(db)
        current_owner = db.get(User, 1)
        if not current_owner or current_owner.password_hash != owner.password_hash:
            raise HTTPException(401, "La contraseña ha cambiado. Vuelve a iniciar sesión.")
        db.execute(delete(LoginSession).where(LoginSession.expires <= now))
        db.add(
            LoginSession(
                token_hash=digest(token), csrf=csrf, expires=now + settings.session_seconds
            )
        )
    response.set_cookie(
        COOKIE,
        token,
        httponly=True,
        secure=settings.secure_cookie,
        samesite="strict",
        max_age=settings.session_seconds,
        path="/",
    )
    return {"name": owner.name, "csrf": csrf}


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)


@router.post("/password", dependencies=[Depends(session)])
def change_password(body: PasswordChange, request: Request, response: Response):
    owner = password_attempt(request)
    try:
        hasher.verify(owner.password_hash if owner else DUMMY_HASH, body.current_password)
    except (VerificationError, InvalidHashError) as error:
        raise HTTPException(400, "La contraseña actual no es correcta.") from error
    if not owner:
        raise HTTPException(401, "Conecta con tu cuenta para continuar.")
    encoded = hasher.hash(body.new_password)
    with connect(request.app.state.settings) as db:
        lock_auth(db)
        current_owner = db.get(User, 1)
        current_session = db.get(LoginSession, digest(request.cookies.get(COOKIE, "")))
        if (
            not current_owner
            or current_owner.password_hash != owner.password_hash
            or not current_session
            or current_session.expires <= int(time.time())
        ):
            raise HTTPException(401, "La sesión ha cambiado. Vuelve a iniciar sesión.")
        current_owner.password_hash = encoded
        db.execute(delete(LoginSession))
    response.delete_cookie(
        COOKIE, secure=request.app.state.settings.secure_cookie, samesite="strict"
    )
    return {"ok": True}


@router.get("/me")
def me(user: Annotated[dict, Depends(session)]):
    return user


@router.post("/logout", dependencies=[Depends(session)])
def logout(request: Request, response: Response):
    with connect(request.app.state.settings) as db:
        db.execute(
            delete(LoginSession).where(
                LoginSession.token_hash == digest(request.cookies[COOKIE]),
            )
        )
    response.delete_cookie(
        COOKIE, secure=request.app.state.settings.secure_cookie, samesite="strict"
    )
    return {"ok": True}
