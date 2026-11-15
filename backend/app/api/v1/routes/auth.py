"""auth.py — Authentication endpoints (Phase 6 M6.2).

Endpoints:
  POST /auth/login   — verify credentials, set HTTP-only session cookie
  POST /auth/logout  — delete session, clear cookie
  GET  /auth/me      — return current user (requires valid session)
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import SESSION_COOKIE_NAME, get_current_user
from app.services import auth_service
from app.services.auth_service import _LockoutError

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=200)


class UserResponse(BaseModel):
    id: str
    username: str
    role: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/auth/login", response_model=UserResponse)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate with username/password.

    On success: sets an HTTP-only ``maar_session`` cookie and returns user info.
    On failure: returns 401.
    On lockout (5 failures in 15 min): returns 429.
    """
    client_ip = (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )

    try:
        user = await auth_service.authenticate_user(
            db, body.username, body.password, ip_address=client_ip
        )
    except _LockoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception("Login exception for username '%s': %s", body.username, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login authentication error: {type(exc).__name__}: {str(exc)}",
        )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    session = await auth_service.create_session(db, user.id, ip_address=client_ip)

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session.id,
        httponly=True,
        samesite="lax",
        secure=(settings.APP_ENV == "production"),
        max_age=3600 * settings.SESSION_TTL_HOURS,
    )

    logger.info("User '%s' logged in from %s.", user.username, client_ip)
    return UserResponse(id=user.id, username=user.username, role=user.role)


@router.post("/auth/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Clear the session cookie and delete the session from the database."""
    token = request.cookies.get(SESSION_COOKIE_NAME) or request.cookies.get("maar_session")
    if token:
        await auth_service.delete_session(db, token)

    response.delete_cookie(key=SESSION_COOKIE_NAME)
    response.delete_cookie(key="maar_session")
    return {"detail": "Logged out"}


@router.get("/auth/me", response_model=UserResponse)
async def get_me(
    current_user=Depends(get_current_user),
):
    """Return the currently authenticated user."""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        role=current_user.role,
    )
