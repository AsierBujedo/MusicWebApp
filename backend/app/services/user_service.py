"""Admin user-management (pure DB logic)."""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.core import security
from app.models.user import User


class UserError(Exception):
    """Domain error mapped to HTTP 400/409 by callers."""


def list_users(db: DbSession) -> List[User]:
    return list(db.scalars(select(User).order_by(User.created_at.asc())).all())


def get_user(db: DbSession, user_id: str) -> Optional[User]:
    return db.get(User, user_id)


def create_user(
    db: DbSession,
    *,
    username: str,
    display_name: str,
    email: Optional[str],
    role: str,
    password: str,
    auto_approve_requests: bool = False,
) -> User:
    normalized = username.strip().lower()
    if not normalized:
        raise UserError("Username is required")
    existing = db.scalar(select(User).where(User.username == normalized))
    if existing is not None:
        raise UserError("Username already taken")

    user = User(
        username=normalized,
        display_name=display_name.strip() or normalized,
        email=(email or "").strip() or None,
        role=role if role in {"ADMIN", "USER"} else "USER",
        auto_approve_requests=bool(auto_approve_requests) if role == "USER" else False,
        active=True,
        must_change_password=True,
        password_hash=security.hash_password(password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(
    db: DbSession,
    user: User,
    *,
    display_name: Optional[str] = None,
    email: Optional[str] = None,
    avatar: Optional[str] = None,
    role: Optional[str] = None,
    auto_approve_requests: Optional[bool] = None,
    active: Optional[bool] = None,
) -> User:
    if display_name is not None:
        user.display_name = display_name.strip() or user.display_name
    if email is not None:
        user.email = email.strip() or None
    if avatar is not None:
        user.avatar = avatar.strip() or None
    if role is not None and role in {"ADMIN", "USER"}:
        user.role = role
        if role == "ADMIN":
            user.auto_approve_requests = False
    if auto_approve_requests is not None and user.role == "USER":
        user.auto_approve_requests = auto_approve_requests
    if active is not None:
        user.active = active
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: DbSession, user: User) -> None:
    db.delete(user)
    db.commit()


def count_admins(db: DbSession) -> int:
    from sqlalchemy import func

    return db.scalar(select(func.count()).select_from(User).where(User.role == "ADMIN")) or 0
