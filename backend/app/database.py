"""Database engine and session management.

We use SQLAlchemy 2.x with a declarative base. The engine is created from
``DATABASE_URL`` so switching from SQLite to PostgreSQL requires no code change:
just point the env var at a Postgres DSN. SQLite-specific ``connect_args`` are
applied only when SQLite is in use.
"""
from __future__ import annotations

import os
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    """Declarative base shared by all ORM models."""


def _make_engine():
    url = settings.database_url
    connect_args: dict = {}
    if url.startswith("sqlite"):
        # Allow use across threads (FastAPI runs handlers in a threadpool).
        connect_args["check_same_thread"] = False
        # Ensure the parent directory exists for file-based SQLite.
        if ":///" in url:
            path = url.split(":///", 1)[1]
            if path and path not in {":memory:"}:
                directory = os.path.dirname(path)
                if directory:
                    os.makedirs(directory, exist_ok=True)
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True, future=True)


engine = _make_engine()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, class_=Session)


def get_db() -> Iterator[Session]:
    """FastAPI dependency that yields a scoped session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
