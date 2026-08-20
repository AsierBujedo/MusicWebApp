from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import new_id, utcnow


class Playlist(Base):
    __tablename__ = "playlists"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    owner_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    cover: Mapped[str | None] = mapped_column(String(512), nullable=True)
    custom_cover_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_shared: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    owner = relationship("User", back_populates="playlists")
    items = relationship(
        "PlaylistTrack",
        back_populates="playlist",
        cascade="all, delete-orphan",
        order_by="PlaylistTrack.position",
    )
    collaborators = relationship("PlaylistCollaborator", cascade="all, delete-orphan")


class PlaylistCollaborator(Base):
    __tablename__ = "playlist_collaborators"
    __table_args__ = (UniqueConstraint("playlist_id", "user_id", name="uq_playlist_collaborator"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    playlist_id: Mapped[str] = mapped_column(ForeignKey("playlists.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    # Collaborators can manage tracks, but changing the playback sequence is
    # opt-in and granted only by the playlist owner.
    can_reorder: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class PlaylistTrack(Base):
    __tablename__ = "playlist_tracks"
    __table_args__ = (
        UniqueConstraint("playlist_id", "track_id", name="uq_playlist_track"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    playlist_id: Mapped[str] = mapped_column(
        ForeignKey("playlists.id", ondelete="CASCADE"), index=True, nullable=False
    )
    track_id: Mapped[str] = mapped_column(
        ForeignKey("tracks.id", ondelete="CASCADE"), index=True, nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    playlist = relationship("Playlist", back_populates="items")
    track = relationship("Track")
