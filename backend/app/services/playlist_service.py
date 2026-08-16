"""Playlist, favorites, and listening-history services."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..models.favorite import Favorite
from ..models.history import HistoryEntry
from ..models.playlist import Playlist, PlaylistTrack
from ..models.user import User


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------- Playlists ----------------

def list_playlists(db: Session, user: User) -> List[Playlist]:
    stmt = select(Playlist).where(Playlist.user_id == user.id).order_by(Playlist.created_at.desc())
    return list(db.scalars(stmt).all())


def get_playlist(db: Session, playlist_id: str) -> Optional[Playlist]:
    return db.get(Playlist, playlist_id)


def create_playlist(db: Session, *, user: User, name: str, description: Optional[str]) -> Playlist:
    pl = Playlist(user_id=user.id, name=name.strip(), description=(description or "").strip() or None)
    db.add(pl)
    db.commit()
    db.refresh(pl)
    return pl


def update_playlist(db: Session, pl: Playlist, *, name: Optional[str], description: Optional[str]) -> Playlist:
    if name is not None:
        pl.name = name.strip()
    if description is not None:
        pl.description = description.strip() or None
    pl.updated_at = _now()
    db.commit()
    db.refresh(pl)
    return pl


def delete_playlist(db: Session, pl: Playlist) -> None:
    db.delete(pl)
    db.commit()


def _next_position(db: Session, playlist_id: str) -> int:
    current = db.scalar(
        select(func.max(PlaylistTrack.position)).where(PlaylistTrack.playlist_id == playlist_id)
    )
    return (current or 0) + 1


def add_track(db: Session, pl: Playlist, track_id: str) -> Playlist:
    exists = db.scalar(
        select(PlaylistTrack).where(
            PlaylistTrack.playlist_id == pl.id, PlaylistTrack.track_id == track_id
        )
    )
    if not exists:
        db.add(
            PlaylistTrack(
                playlist_id=pl.id,
                track_id=track_id,
                position=_next_position(db, pl.id),
            )
        )
        pl.updated_at = _now()
        db.commit()
        db.refresh(pl)
    return pl


def remove_track(db: Session, pl: Playlist, track_id: str) -> Playlist:
    db.execute(
        delete(PlaylistTrack).where(
            PlaylistTrack.playlist_id == pl.id, PlaylistTrack.track_id == track_id
        )
    )
    pl.updated_at = _now()
    db.commit()
    db.refresh(pl)
    return pl


def reorder_tracks(db: Session, pl: Playlist, ordered_track_ids: List[str]) -> Playlist:
    rows = {pt.track_id: pt for pt in pl.tracks}
    for index, track_id in enumerate(ordered_track_ids, start=1):
        if track_id in rows:
            rows[track_id].position = index
    pl.updated_at = _now()
    db.commit()
    db.refresh(pl)
    return pl


# ---------------- Favorites ----------------

def list_favorite_ids(db: Session, user: User) -> List[str]:
    stmt = (
        select(Favorite.track_id)
        .where(Favorite.user_id == user.id)
        .order_by(Favorite.created_at.desc())
    )
    return list(db.scalars(stmt).all())


def is_favorite(db: Session, user: User, track_id: str) -> bool:
    return db.scalar(
        select(Favorite).where(Favorite.user_id == user.id, Favorite.track_id == track_id)
    ) is not None


def add_favorite(db: Session, user: User, track_id: str) -> None:
    if not is_favorite(db, user, track_id):
        db.add(Favorite(user_id=user.id, track_id=track_id))
        db.commit()


def remove_favorite(db: Session, user: User, track_id: str) -> None:
    db.execute(
        delete(Favorite).where(Favorite.user_id == user.id, Favorite.track_id == track_id)
    )
    db.commit()


# ---------------- History ----------------

def record_play(db: Session, user: User, track_id: str) -> HistoryEntry:
    entry = HistoryEntry(user_id=user.id, track_id=track_id, played_at=_now())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    _trim_history(db, user)
    return entry


def _trim_history(db: Session, user: User) -> None:
    ids = list(
        db.scalars(
            select(HistoryEntry.id)
            .where(HistoryEntry.user_id == user.id)
            .order_by(HistoryEntry.played_at.desc())
            .offset(settings.history_max_entries)
        ).all()
    )
    if ids:
        db.execute(delete(HistoryEntry).where(HistoryEntry.id.in_(ids)))
        db.commit()


def list_history(db: Session, user: User, limit: int = 100) -> List[HistoryEntry]:
    stmt = (
        select(HistoryEntry)
        .where(HistoryEntry.user_id == user.id)
        .order_by(HistoryEntry.played_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


def clear_history(db: Session, user: User) -> None:
    db.execute(delete(HistoryEntry).where(HistoryEntry.user_id == user.id))
    db.commit()
