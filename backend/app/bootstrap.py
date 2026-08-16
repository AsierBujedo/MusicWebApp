"""First-run bootstrap: ensure an admin account exists.

Runs on startup. It NEVER overwrites existing data — it only creates the initial
admin (and an optional demo user in non-production) when the users table is
empty, so a fresh deployment is immediately usable. Credentials come from
``BOOTSTRAP_ADMIN_*`` env vars, falling back to ``admin`` / ``admin`` in
development only.
"""
from __future__ import annotations

import logging

from sqlalchemy import func, select

from app.config import settings
from app.core import security
from app.database import SessionLocal
from app.models.user import User

logger = logging.getLogger(__name__)


def ensure_bootstrap_admin() -> None:
    db = SessionLocal()
    try:
        user_count = db.scalar(select(func.count()).select_from(User)) or 0
        if user_count > 0:
            return

        username = (settings.bootstrap_admin_username or "").strip().lower()
        password = settings.bootstrap_admin_password
        if not username or not password:
            if settings.is_production:
                logger.warning(
                    "No users exist and BOOTSTRAP_ADMIN_USERNAME/PASSWORD are unset in production; "
                    "no admin was created. Set them and restart."
                )
                return
            username, password = "admin", "admin"
            logger.warning("Seeding development admin 'admin'/'admin'. Change this immediately.")

        admin = User(
            username=username,
            display_name=settings.bootstrap_admin_display_name or "Admin",
            role="ADMIN",
            active=True,
            password_hash=security.hash_password(password),
        )
        db.add(admin)

        if not settings.is_production:
            db.add(
                User(
                    username="demo",
                    display_name="Demo User",
                    role="USER",
                    active=True,
                    password_hash=security.hash_password("demo1234"),
                )
            )
        db.commit()
        logger.info("Bootstrap admin '%s' created.", username)
    finally:
        db.close()
