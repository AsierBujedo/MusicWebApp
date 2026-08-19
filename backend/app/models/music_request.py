from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import new_id, utcnow


class MusicRequest(Base):
    __tablename__ = "music_requests"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    requested_by: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # "track" | "album" | "artist"
    type: Mapped[str] = mapped_column(String(16), nullable=False, default="track")
    track_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    # Identifiers owned by DroppedNeedle. They stay server-side and let the
    # worker correlate this private request with the remote acquisition.
    musicbrainz_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    # Denormalized display fields so a request survives even if the source track
    # metadata changes or disappears.
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    artist: Mapped[str] = mapped_column(String(512), nullable=False)
    cover: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # PENDING | APPROVED | SEARCHING | DOWNLOADING | AVAILABLE | FAILED | REJECTED
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING", index=True)
    progress: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Soulseek availability changes constantly. When no matching release is
    # found, Resonar keeps the request and schedules a later re-search instead
    # of requiring the requester to manually press retry every time.
    soulseek_retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    soulseek_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    user = relationship("User")
