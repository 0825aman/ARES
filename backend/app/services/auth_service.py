"""auth_service.py — Authentication business logic (Phase 6 M6.2).

Responsibilities:
  - Seed the admin user at startup (from env vars)
  - Authenticate username/password with brute-force protection
  - Create / delete sessions
  - Look up a session token to retrieve the associated user
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import generate_session_token, hash_password, verify_password
from app.models.user import LoginAttempt, Session, User

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """Return current UTC time as an offset-naive datetime.
    
    Compatible with both SQLite and PostgreSQL TIMESTAMP WITHOUT TIME ZONE columns in asyncpg.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Startup seeding
# ---------------------------------------------------------------------------


async def seed_admin_user(db: AsyncSession) -> None:
    """Create the admin user if no users exist.

    Called once at application startup. Uses ADMIN_USERNAME and
    ADMIN_PASSWORD_HASH from environment. If ADMIN_PASSWORD_HASH is empty,
    logs a warning and skips creation (auth will be unenforced until set).
    """
    result = await db.execute(select(func.count()).select_from(User))
    count = result.scalar_one()
    if count > 0:
        return  # Users already exist — do not overwrite

    if not settings.ADMIN_PASSWORD_HASH:
        logger.warning(
            "ADMIN_PASSWORD_HASH is not set. "
            "Authentication is disabled until a password hash is configured. "
            "Generate one with: "
            "python -c \"import bcrypt; print(bcrypt.hashpw(b'yourpassword', bcrypt.gensalt()).decode())\""
        )
        return

    now = _utcnow()
    admin = User(
        username=settings.ADMIN_USERNAME,
        hashed_password=settings.ADMIN_PASSWORD_HASH,
        role="admin",
        is_active=True,
        created_at=now,
    )
    db.add(admin)
    await db.commit()
    logger.info("Seeded admin user '%s'.", settings.ADMIN_USERNAME)


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


async def authenticate_user(
    db: AsyncSession,
    username: str,
    password: str,
    ip_address: str = "unknown",
) -> Optional[User]:
    """Verify credentials with brute-force protection.

    Returns the User on success, None on failure.
    Raises HTTP 429 (via ValueError with special prefix) when locked out.
    Records every attempt in login_attempts for audit + rate limiting.
    """
    # Self-healing: if no users exist in database, seed admin user on-demand
    user_count_result = await db.execute(select(func.count()).select_from(User))
    if user_count_result.scalar_one() == 0:
        await seed_admin_user(db)

    now = _utcnow()
    lockout_window = now - timedelta(minutes=settings.AUTH_LOCKOUT_MINUTES)

    # Count recent failed attempts for this username
    fail_count_result = await db.execute(
        select(func.count()).select_from(LoginAttempt).where(
            LoginAttempt.username == username,
            LoginAttempt.succeeded == False,  # noqa: E712
            LoginAttempt.attempted_at >= lockout_window,
        )
    )
    fail_count = fail_count_result.scalar_one()

    if fail_count >= settings.AUTH_MAX_ATTEMPTS:
        logger.warning(
            "Login blocked for '%s' from %s — %d failed attempts in %d minutes.",
            username, ip_address, fail_count, settings.AUTH_LOCKOUT_MINUTES,
        )
        raise _LockoutError(
            f"Too many failed attempts. Try again after {settings.AUTH_LOCKOUT_MINUTES} minutes."
        )

    # Fetch user
    user_result = await db.execute(
        select(User).where(User.username == username, User.is_active == True)  # noqa: E712
    )
    user = user_result.scalar_one_or_none()

    succeeded = user is not None and verify_password(password, user.hashed_password)

    # Record the attempt
    attempt = LoginAttempt(
        username=username,
        ip_address=ip_address,
        succeeded=succeeded,
        attempted_at=now,
    )
    db.add(attempt)

    if succeeded and user is not None:
        user.last_login = now
        await db.commit()
        return user

    await db.commit()
    return None


class _LockoutError(Exception):
    """Raised when a user is locked out due to too many failed login attempts."""


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------


async def create_session(
    db: AsyncSession,
    user_id: str,
    ip_address: str = "unknown",
) -> Session:
    """Create a new session for the given user. Commits to DB."""
    token = generate_session_token()
    now = _utcnow()
    session = Session(
        id=token,
        user_id=user_id,
        expires_at=now + timedelta(hours=settings.SESSION_TTL_HOURS),
        created_at=now,
        ip_address=ip_address,
    )
    db.add(session)
    await db.commit()
    return session


async def delete_session(db: AsyncSession, token: str) -> None:
    """Delete the session with the given token. No-op if not found."""
    result = await db.execute(select(Session).where(Session.id == token))
    session = result.scalar_one_or_none()
    if session:
        await db.delete(session)
        await db.commit()


async def get_user_by_session_token(
    db: AsyncSession,
    token: str,
) -> Optional[User]:
    """Return the User associated with a valid, non-expired session token.

    Returns None if the token doesn't exist or the session has expired.
    Automatically marks expired sessions (does not delete them — audit trail).
    """
    result = await db.execute(
        select(Session).where(Session.id == token)
    )
    session = result.scalar_one_or_none()
    if session is None:
        return None

    now = _utcnow()
    exp = session.expires_at
    if exp.tzinfo is not None:
        exp = exp.astimezone(timezone.utc).replace(tzinfo=None)

    if now > exp:
        # Expired — clean up
        await db.delete(session)
        await db.commit()
        return None

    # Load the associated user
    user_result = await db.execute(
        select(User).where(User.id == session.user_id, User.is_active == True)  # noqa: E712
    )
    return user_result.scalar_one_or_none()
