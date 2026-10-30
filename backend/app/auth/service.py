"""Users and browser login sessions. Only a SHA-256 of the cookie token is stored."""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.oidc import Identity
from app.config import Settings
from app.db.models import AuthSession, User


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def upsert_user(db: AsyncSession, identity: Identity) -> User:
    """Create the user or refresh its display data in one statement, so two first sign-ins both work."""
    statement = (
        pg_insert(User)
        .values(issuer=identity.issuer, subject=identity.subject, email=identity.email, name=identity.name)
        .on_conflict_do_update(
            constraint="uq_users_issuer_subject",
            set_={
                "email": func.coalesce(identity.email, User.email),
                "name": func.coalesce(identity.name, User.name),
            },
        )
        .returning(User)
    )
    return (await db.execute(statement.execution_options(populate_existing=True))).scalar_one()


async def start_session(db: AsyncSession, user: User, settings: Settings) -> str:
    token = secrets.token_urlsafe(32)
    db.add(
        AuthSession(
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=datetime.now(UTC) + timedelta(seconds=settings.auth_session_ttl_seconds),
        )
    )
    await db.commit()
    return token


async def user_for_token(db: AsyncSession, token: str | None) -> User | None:
    if not token:
        return None
    row = (
        await db.execute(
            select(User)
            .join(AuthSession, AuthSession.user_id == User.id)
            .where(
                AuthSession.token_hash == hash_token(token),
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > datetime.now(UTC),
            )
        )
    ).scalar_one_or_none()
    return row


async def revoke(db: AsyncSession, token: str | None) -> None:
    if token:
        await db.execute(
            update(AuthSession)
            .where(AuthSession.token_hash == hash_token(token), AuthSession.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
        await db.commit()


def validate_settings(settings: Settings) -> None:
    """Fail closed: a production deployment must sign people in through a real provider."""
    passcode_only = (
        settings.auth_mode == "off"
        and settings.allow_passcode_only_production
        and bool(settings.demo_passcode)
    )
    if settings.app_env == "production" and settings.auth_mode != "oidc" and not passcode_only:
        raise RuntimeError(
            "AUTH_MODE must be 'oidc' in production (or ALLOW_PASSCODE_ONLY_PRODUCTION=true with a "
            "DEMO_PASSCODE for a passcode-only demo)."
        )
    if settings.auth_mode == "test" and settings.app_env == "production":
        raise RuntimeError("The test sign-in provider is not allowed in production.")
    if settings.auth_mode != "off" and len(settings.auth_secret_key) < 32:
        raise RuntimeError("AUTH_SECRET_KEY (at least 32 characters) is required when authentication is on.")
    local = settings.public_origin.startswith(("http://localhost", "http://127.0.0.1"))
    both_secure = settings.auth_cookie_secure and settings.session_cookie_secure
    if settings.app_env == "production" and not local and not both_secure:
        raise RuntimeError(
            "AUTH_COOKIE_SECURE and SESSION_COOKIE_SECURE must be true in production: "
            "the sign-in cookie must never travel over plain HTTP."
        )
    if settings.auth_mode == "oidc" and not (settings.oidc_issuer and settings.oidc_client_id):
        raise RuntimeError("OIDC_ISSUER and OIDC_CLIENT_ID are required for OIDC sign-in.")


async def latest_session_id(db: AsyncSession, user: User) -> uuid.UUID | None:
    from app.db.models import Session

    return (
        await db.execute(
            select(Session.id)
            .where(Session.owner_user_id == user.id)
            .order_by(Session.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
