"""Authorization helpers.

Authorization is always enforced server-side. Ownership checks prefer returning
404 for resources the caller must not even know exist (private playlists,
other users' requests) to avoid disclosing their existence.
"""
from __future__ import annotations

from fastapi import HTTPException, status

from app.models.user import User

ROLE_ADMIN = "ADMIN"
ROLE_USER = "USER"


def is_admin(user: User) -> bool:
    return user.role == ROLE_ADMIN


def require_admin(user: User) -> None:
    if not is_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def ensure_owner_or_admin(user: User, owner_id: str, *, hide: bool = True) -> None:
    """Ensure ``user`` owns the resource or is an admin.

    ``hide=True`` returns 404 instead of 403 so the resource's existence is not
    disclosed to unauthorized users.
    """
    if is_admin(user) or user.id == owner_id:
        return
    if hide:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
