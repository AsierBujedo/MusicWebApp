"""Shared column helpers for ORM models."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone


def new_id() -> str:
    """Opaque, URL-safe primary key. Hides internal ordering/sequence info."""
    return uuid.uuid4().hex


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime | None) -> str | None:
    """Serialize a datetime to an ISO-8601 UTC string, tolerating the naive
    datetimes SQLite returns (treated as UTC)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()
