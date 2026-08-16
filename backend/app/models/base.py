"""Shared column helpers for ORM models."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone


def new_id() -> str:
    """Opaque, URL-safe primary key. Hides internal ordering/sequence info."""
    return uuid.uuid4().hex


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
