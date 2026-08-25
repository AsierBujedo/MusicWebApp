"""Instance-level operational switches.

These settings intentionally live in the application database rather than an
environment variable so an administrator can enable maintenance mode without a
redeploy. Missing rows use the safe normal default (downloads enabled).
"""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session as DbSession

from app.models.system_setting import SystemSetting

DOWNLOADS_ENABLED_KEY = "downloads_enabled"
DOWNLOADS_UNAVAILABLE_MESSAGE = "Las descargas de canciones están temporalmente fuera de servicio."


def downloads_enabled(db: DbSession) -> bool:
    setting = db.get(SystemSetting, DOWNLOADS_ENABLED_KEY)
    return True if setting is None else setting.enabled


def set_downloads_enabled(db: DbSession, enabled: bool) -> bool:
    setting = db.get(SystemSetting, DOWNLOADS_ENABLED_KEY)
    if setting is None:
        setting = SystemSetting(key=DOWNLOADS_ENABLED_KEY, enabled=enabled)
        db.add(setting)
    else:
        setting.enabled = enabled
    db.commit()
    return setting.enabled


def require_downloads_enabled(db: DbSession) -> None:
    if not downloads_enabled(db):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=DOWNLOADS_UNAVAILABLE_MESSAGE)
