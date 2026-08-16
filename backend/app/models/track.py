from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import new_id, utcnow


class Track(Base):
    """A backend-level track. Uses a stable opaque ``id`` so internal provider
    IDs and file paths never leak to the browser."""

    __tablename__ = "tracks"
    __table_args__ = (
        UniqueConstraint("provider", "provider_id", name="uq_track_provider"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)

    # Origin of the metadata: "navidrome", "droppedneedle", "local", "external"...
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="local", index=True)
    provider_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    artist: Mapped[str] = mapped_column(String(512), nullable=False)
    artist_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    album: Mapped[str | None] = mapped_column(String(512), nullable=True)
    album_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    cover: Mapped[str | None] = mapped_column(String(512), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True)  # seconds

    # Availability status: AVAILABLE | REQUESTABLE | PENDING | DOWNLOADING | UNAVAILABLE
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="REQUESTABLE", index=True)
    available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    progress: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Opaque internal reference to the playable resource (never sent to clients).
    file_reference: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
