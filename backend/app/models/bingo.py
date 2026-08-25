from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import new_id, utcnow


class BingoGame(Base):
    __tablename__ = "bingo_games"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    host_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    playlist_id: Mapped[str] = mapped_column(ForeignKey("playlists.id", ondelete="CASCADE"), index=True)
    join_code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="LOBBY")
    grid_size: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    play_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    mark_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=8)
    sequence_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    current_index: Mapped[int] = mapped_column(Integer, nullable=False, default=-1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class BingoPlayer(Base):
    __tablename__ = "bingo_players"
    __table_args__ = (UniqueConstraint("game_id", "guest_token", name="uq_bingo_player_token"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    game_id: Mapped[str] = mapped_column(ForeignKey("bingo_games.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    guest_token: Mapped[str] = mapped_column(String(48), nullable=False, default=new_id)
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    card_json: Mapped[str] = mapped_column(Text, nullable=False)
    marked_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class BingoClaim(Base):
    __tablename__ = "bingo_claims"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    game_id: Mapped[str] = mapped_column(ForeignKey("bingo_games.id", ondelete="CASCADE"), index=True)
    player_id: Mapped[str] = mapped_column(ForeignKey("bingo_players.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(12), nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
