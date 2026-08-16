"""Reusable FastAPI dependencies for authentication and authorization."""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session as DbSession

from app.config import settings
from app.core.permissions import require_admin
from app.database import get_db
from app.models.user import User
from app.services import auth_service


def get_current_user(request: Request, db: DbSession = Depends(get_db)) -> User:
    """Resolve the authenticated user from the HttpOnly session cookie."""
    raw_token = request.cookies.get(settings.session_cookie_name, "")
    resolved = auth_service.resolve_session(db, raw_token)
    if resolved is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    _session, user = resolved
    return user


def get_current_admin(user: User = Depends(get_current_user)) -> User:
    require_admin(user)
    return user
