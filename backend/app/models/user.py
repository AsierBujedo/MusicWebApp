from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import new_id, utcnow


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # "ADMIN" or "USER" — stored as string to match the frontend contract exactly.
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="USER")
    # Allows a trusted regular user to bypass the moderation queue. It never
    # grants administrative access.
    auto_approve_requests: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Set for accounts provisioned by an administrator. It is cleared only
    # after the account holder successfully changes the initial password.
    must_change_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    playlists = relationship("Playlist", back_populates="owner", cascade="all, delete-orphan")
    feature_flags = relationship("UserFeatureFlag", cascade="all, delete-orphan")


class UserFeatureFlag(Base):
    __tablename__ = "user_feature_flags"
    __table_args__ = (UniqueConstraint("user_id", "feature_key", name="uq_user_feature_flag"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    feature_key: Mapped[str] = mapped_column(String(64), nullable=False)
