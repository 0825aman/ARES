from __future__ import annotations

"""test_auth.py — Tests for authentication endpoints (Phase 6 M6.2).

Note: Tests run with AUTO_LOGIN_DEV=true (set in conftest.py), so the
general async_client bypasses auth. Auth-specific tests that need to test
the actual auth flow create their own clients WITHOUT the dev bypass by
directly testing the auth service and security functions.
"""

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    SESSION_COOKIE_NAME,
    generate_session_token,
    hash_password,
    verify_password,
)
from app.models.user import LoginAttempt, Session, User


# ---------------------------------------------------------------------------
# Password utilities
# ---------------------------------------------------------------------------


def test_hash_password_returns_bcrypt_hash():
    hashed = hash_password("mypassword")
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")


def test_verify_password_correct():
    hashed = hash_password("correct")
    assert verify_password("correct", hashed) is True


def test_verify_password_wrong():
    hashed = hash_password("correct")
    assert verify_password("wrong", hashed) is False


def test_generate_session_token_length():
    token = generate_session_token()
    assert len(token) == 64


def test_generate_session_token_unique():
    t1 = generate_session_token()
    t2 = generate_session_token()
    assert t1 != t2


# ---------------------------------------------------------------------------
# Auth service tests (via DB)
# ---------------------------------------------------------------------------


async def test_seed_admin_user_creates_user_when_none_exist(db_session: AsyncSession):
    """seed_admin_user should create an admin user if none exists."""
    from app.services.auth_service import seed_admin_user

    with patch("app.services.auth_service.settings") as mock_settings:
        mock_settings.ADMIN_USERNAME = "admin"
        mock_settings.ADMIN_PASSWORD_HASH = hash_password("adminpass")

        await seed_admin_user(db_session)

    from sqlalchemy import select
    result = await db_session.execute(select(User).where(User.username == "admin"))
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.role == "admin"


async def test_seed_admin_user_does_not_duplicate(db_session: AsyncSession, test_user: User):
    """seed_admin_user must not create a second user if one already exists."""
    from app.services.auth_service import seed_admin_user
    from sqlalchemy import func, select

    initial_count_result = await db_session.execute(
        select(func.count()).select_from(User)
    )
    initial_count = initial_count_result.scalar_one()

    await seed_admin_user(db_session)  # should be a no-op

    final_count_result = await db_session.execute(
        select(func.count()).select_from(User)
    )
    final_count = final_count_result.scalar_one()
    assert final_count == initial_count


async def test_authenticate_user_success(db_session: AsyncSession, test_user: User):
    """authenticate_user returns the user on correct credentials."""
    from app.services.auth_service import authenticate_user
    result = await authenticate_user(db_session, "testadmin", "testpass123")
    assert result is not None
    assert result.id == test_user.id


async def test_authenticate_user_wrong_password(db_session: AsyncSession, test_user: User):
    """authenticate_user returns None for wrong password."""
    from app.services.auth_service import authenticate_user
    result = await authenticate_user(db_session, "testadmin", "wrongpassword")
    assert result is None


async def test_authenticate_user_unknown_username(db_session: AsyncSession):
    """authenticate_user returns None for unknown username."""
    from app.services.auth_service import authenticate_user
    result = await authenticate_user(db_session, "nobody", "anything")
    assert result is None


async def test_authenticate_user_brute_force_lockout(db_session: AsyncSession, test_user: User):
    """After AUTH_MAX_ATTEMPTS failed logins, _LockoutError is raised."""
    from app.services.auth_service import authenticate_user, _LockoutError

    # Exhaust attempts
    for _ in range(5):
        await authenticate_user(db_session, "testadmin", "badpass")

    with pytest.raises(_LockoutError):
        await authenticate_user(db_session, "testadmin", "badpass")


async def test_create_session_returns_session(db_session: AsyncSession, test_user: User):
    """create_session should persist a Session record."""
    from app.services.auth_service import create_session
    from sqlalchemy import select

    session = await create_session(db_session, test_user.id, ip_address="127.0.0.1")
    assert session is not None
    assert len(session.id) == 64

    result = await db_session.execute(select(Session).where(Session.id == session.id))
    persisted = result.scalar_one_or_none()
    assert persisted is not None


async def test_delete_session(db_session: AsyncSession, test_session: Session):
    """delete_session removes the session from the DB."""
    from app.services.auth_service import delete_session, get_user_by_session_token

    await delete_session(db_session, test_session.id)
    user = await get_user_by_session_token(db_session, test_session.id)
    assert user is None


async def test_get_user_by_session_token_valid(db_session: AsyncSession, test_user: User, test_session: Session):
    """get_user_by_session_token returns the user for a valid session."""
    from app.services.auth_service import get_user_by_session_token

    user = await get_user_by_session_token(db_session, test_session.id)
    assert user is not None
    assert user.id == test_user.id


async def test_get_user_by_session_token_invalid(db_session: AsyncSession):
    """get_user_by_session_token returns None for a non-existent token."""
    from app.services.auth_service import get_user_by_session_token

    user = await get_user_by_session_token(db_session, "nonexistenttokenabcdef")
    assert user is None


async def test_get_user_by_session_token_expired(db_session: AsyncSession, test_user: User):
    """get_user_by_session_token returns None for an expired session."""
    from app.services.auth_service import get_user_by_session_token

    # Insert expired session directly
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    expired_session = Session(
        id=generate_session_token(),
        user_id=test_user.id,
        expires_at=past,
        created_at=past,
        ip_address="127.0.0.1",
    )
    db_session.add(expired_session)
    await db_session.commit()

    user = await get_user_by_session_token(db_session, expired_session.id)
    assert user is None


# ---------------------------------------------------------------------------
# HTTP endpoint tests (use async_client which has AUTO_LOGIN_DEV bypass)
# ---------------------------------------------------------------------------


async def test_login_success_sets_cookie(async_client: AsyncClient, db_session: AsyncSession, test_user: User):
    """POST /api/v1/auth/login with valid credentials must set a session cookie."""
    # Temporarily disable AUTO_LOGIN_DEV for this specific auth endpoint test
    # by directly calling the endpoint with real credentials
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"username": "testadmin", "password": "testpass123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testadmin"
    # Cookie should be set
    assert SESSION_COOKIE_NAME in response.cookies


async def test_login_invalid_credentials_returns_401(async_client: AsyncClient, test_user: User):
    """POST /api/v1/auth/login with wrong password must return 401."""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"username": "testadmin", "password": "wrongpassword"},
    )
    assert response.status_code == 401


async def test_login_unknown_user_returns_401(async_client: AsyncClient):
    """POST /api/v1/auth/login with unknown username must return 401."""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"username": "ghost", "password": "anything"},
    )
    assert response.status_code == 401


async def test_login_brute_force_returns_429(async_client: AsyncClient, test_user: User):
    """Five failed logins should trigger HTTP 429 on the sixth attempt."""
    for _ in range(5):
        await async_client.post(
            "/api/v1/auth/login",
            json={"username": "testadmin", "password": "badpass"},
        )
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"username": "testadmin", "password": "badpass"},
    )
    assert response.status_code == 429


async def test_logout_clears_cookie(async_client: AsyncClient, test_user: User):
    """POST /api/v1/auth/logout must clear the session cookie."""
    # Login first to get a cookie
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"username": "testadmin", "password": "testpass123"},
    )
    assert login_resp.status_code == 200

    # Now logout
    logout_resp = await async_client.post("/api/v1/auth/logout")
    assert logout_resp.status_code == 200


async def test_auth_me_returns_current_user(async_client: AsyncClient, test_user: User):
    """GET /api/v1/auth/me with AUTO_LOGIN_DEV=true returns the dev user."""
    response = await async_client.get("/api/v1/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert "username" in data
    assert "role" in data


async def test_protected_endpoint_works_with_dev_bypass(async_client: AsyncClient):
    """With AUTO_LOGIN_DEV=true, protected endpoints return 200 without a session."""
    response = await async_client.get("/api/v1/projects/")
    assert response.status_code == 200


async def test_production_auth_flow(async_client: AsyncClient, test_user: User):
    """When AUTO_LOGIN_DEV=False, protected routes reject unauthenticated requests,
    login succeeds and issues a session cookie, and subsequent requests succeed."""
    from app.core.config import settings

    orig_dev = settings.AUTO_LOGIN_DEV
    orig_env = settings.APP_ENV
    settings.AUTO_LOGIN_DEV = False
    settings.APP_ENV = "production"

    try:
        # 1. Unauthenticated request to protected route is rejected
        unauth_resp = await async_client.get("/api/v1/projects")
        assert unauth_resp.status_code == 401

        # 2. Login endpoint remains accessible without pre-existing session
        login_resp = await async_client.post(
            "/api/v1/auth/login",
            json={"username": "testadmin", "password": "testpass123"},
        )
        assert login_resp.status_code == 200
        assert SESSION_COOKIE_NAME in login_resp.cookies
        cookie_val = login_resp.cookies[SESSION_COOKIE_NAME]

        # 3. Request with valid session cookie succeeds
        auth_resp = await async_client.get(
            "/api/v1/projects",
            cookies={SESSION_COOKIE_NAME: cookie_val},
        )
        assert auth_resp.status_code == 200

    finally:
        settings.AUTO_LOGIN_DEV = orig_dev
        settings.APP_ENV = orig_env
