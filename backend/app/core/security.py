"""security.py — Password hashing, session tokens, and authentication dependency.

Provides:
  - hash_password / verify_password   (bcrypt)
  - generate_session_token            (64-char cryptographic hex)
  - get_current_user                  (FastAPI dependency — raises 401 if not authenticated)
  - require_auth                      (shorthand dependency alias)
"""
from __future__ import annotations

import logging
import secrets
from typing import Annotated

import bcrypt
from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Password utilities
# ---------------------------------------------------------------------------


def hash_password(plain: str) -> str:
    """Hash a plain-text password with bcrypt. Returns the hash as a string."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain matches the bcrypt hash."""
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Session token
# ---------------------------------------------------------------------------


def generate_session_token() -> str:
    """Return a 64-character cryptographic hex string for use as a session token."""
    return secrets.token_hex(32)  # 32 bytes = 64 hex chars


# ---------------------------------------------------------------------------
# FastAPI dependency — authenticated user
# ---------------------------------------------------------------------------

#: Name of the HTTP-only session cookie
SESSION_COOKIE_NAME = "ares_session"
LEGACY_SESSION_COOKIE_NAME = "maar_session"


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """FastAPI dependency that returns the authenticated User, or raises HTTP 401.

    Reads the session token from the ``ares_session`` cookie (falling back to legacy ``maar_session``).
    Dev bypass: if ``AUTO_LOGIN_DEV=True``, returns a synthetic user object
    without touching the database (for local development without a password).
    """
    from app.models.user import User

    # Dev bypass — skip auth in development when AUTO_LOGIN_DEV=true
    if settings.AUTO_LOGIN_DEV and settings.APP_ENV == "development":
        return _dev_user()

    token = request.cookies.get(SESSION_COOKIE_NAME) or request.cookies.get(LEGACY_SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    from app.services import auth_service
    user = await auth_service.get_user_by_session_token(db, token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid",
        )
    return user


class _DevUser:
    """Lightweight stand-in for a User in AUTO_LOGIN_DEV mode.

    Not a SQLAlchemy model — avoids the _sa_instance_state requirement.
    Only the fields accessed by auth routes (id, username, role) are populated.
    """
    def __init__(self):
        from datetime import datetime, timezone
        self.id = "dev-user-00000000-0000-0000-0000-000000000000"
        self.username = "dev"
        self.role = "admin"
        self.is_active = True
        self.created_at = datetime.now(timezone.utc)
        self.last_login = None
        self.hashed_password = ""


def _dev_user() -> _DevUser:
    """Return a synthetic user object for AUTO_LOGIN_DEV mode."""
    return _DevUser()


# Convenience alias for use in route signatures
CurrentUser = Annotated[object, Depends(get_current_user)]
