"""Authentication & session business logic (framework-agnostic)."""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.config import settings
from app.core import security
from app.models.base import utcnow
from app.models.session import Session as SessionModel
from app.models.user import User


class AuthError(Exception):
    """Raised for authentication failures. Callers map this to HTTP 401."""


def authenticate(db: DbSession, username: str, password: str) -> User:
    """Return the user on success. Raises ``AuthError`` on any failure without
    revealing whether the username or the password was wrong."""
    normalized = username.strip().lower()
    user = db.scalar(
        select(User).where((User.username == normalized) | (User.email == normalized))
    )
    # Always run a verification to keep timing roughly constant even for unknown
    # usernames, then decide.
    if user is None:
        security.verify_password(password, security.hash_password("dummy-timing-guard"))
        raise AuthError("invalid credentials")

    if not security.verify_password(password, user.password_hash):
        raise AuthError("invalid credentials")

    if not user.active:
        raise AuthError("inactive account")

    # Opportunistically upgrade the hash if parameters changed.
    if security.needs_rehash(user.password_hash):
        user.password_hash = security.hash_password(password)
        db.commit()

    user.last_seen = utcnow()
    db.commit()
    return user


def create_session(db: DbSession, user: User) -> str:
    """Create a session row and return the *raw* token for the cookie."""
    raw_token = security.generate_session_token()
    now = utcnow()
    session = SessionModel(
        user_id=user.id,
        token_hash=security.hash_token(raw_token),
        created_at=now,
        expires_at=now + timedelta(seconds=settings.session_ttl_seconds),
        last_seen=now,
    )
    db.add(session)
    db.commit()
    return raw_token


def resolve_session(db: DbSession, raw_token: str) -> tuple[SessionModel, User] | None:
    """Return (session, user) for a valid, unexpired token, else ``None``.
    Expired sessions are pruned as a side effect."""
    if not raw_token:
        return None
    token_hash = security.hash_token(raw_token)
    session = db.scalar(select(SessionModel).where(SessionModel.token_hash == token_hash))
    if session is None:
        return None

    now = utcnow()
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        # SQLite may return naive datetimes; treat as UTC.
        from datetime import timezone

        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        db.delete(session)
        db.commit()
        return None

    user = db.get(User, session.user_id)
    if user is None or not user.active:
        return None

    # Throttled last-seen refresh (avoid a write on every request).
    last_seen = session.last_seen
    if last_seen.tzinfo is None:
        from datetime import timezone

        last_seen = last_seen.replace(tzinfo=timezone.utc)
    if (now - last_seen).total_seconds() > 60:
        session.last_seen = now
        user.last_seen = now
        db.commit()

    return session, user


def revoke_session(db: DbSession, raw_token: str) -> None:
    if not raw_token:
        return
    token_hash = security.hash_token(raw_token)
    session = db.scalar(select(SessionModel).where(SessionModel.token_hash == token_hash))
    if session is not None:
        db.delete(session)
        db.commit()


def change_password(db: DbSession, user: User, current_password: str, new_password: str) -> None:
    if not security.verify_password(current_password, user.password_hash):
        raise AuthError("current password incorrect")
    user.password_hash = security.hash_password(new_password)
    user.must_change_password = False
    db.commit()


def update_email(db: DbSession, user: User, email: str) -> User:
    normalized = email.strip().lower()
    if not normalized or "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
        raise AuthError("invalid email")
    existing = db.scalar(select(User).where(User.email == normalized, User.id != user.id))
    if existing is not None:
        raise AuthError("email already used")
    user.email = normalized
    db.commit()
    db.refresh(user)
    return user
