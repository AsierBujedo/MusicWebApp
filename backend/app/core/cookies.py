"""Session-cookie helpers.

The session cookie is always ``HttpOnly`` (JS can never read it) and scoped to
``/``. ``SameSite``/``Secure`` are chosen from configuration:

- Same-origin production behind a reverse proxy: ``SameSite=Lax`` is enough.
- Cross-origin dev / preview (a configured ``FRONTEND_ORIGIN``): browsers only
  send a cross-site cookie when it is ``SameSite=None`` **and** ``Secure``.
"""
from __future__ import annotations

from fastapi import Response

from app.config import settings


def _cookie_policy() -> tuple[str, bool]:
    cross_site = bool(settings.cors_origins)
    if cross_site:
        return "none", True  # Secure required alongside SameSite=None
    return "lax", settings.is_production


def set_session_cookie(response: Response, token: str) -> None:
    samesite, secure = _cookie_policy()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        samesite=samesite,
        secure=secure,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    samesite, secure = _cookie_policy()
    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=True,
        samesite=samesite,
        secure=secure,
        path="/",
    )
