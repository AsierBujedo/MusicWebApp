"""Playlists, favorites, and listening-history (pure DB logic)."""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session as DbSession

from app.config import settings
from app.models.base import utcnow
from app.models.favorite import Favorite
from app.models.history import History
from app.models.playlist import Playlist, PlaylistCollaborator, PlaylistTrack
from app.models.track import Track
from app.models.user import User


class PlaylistError(Exception):
    """Domain error mapped to HTTP 400 by callers."""


# ----------------------------- Playlists -----------------------------

def list_playlists(db: DbSession, user: User) -> List[Playlist]:
    stmt = (
        select(Playlist)
        .outerjoin(PlaylistCollaborator, PlaylistCollaborator.playlist_id == Playlist.id)
        .where((Playlist.owner_user_id == user.id) | (PlaylistCollaborator.user_id == user.id))
        .distinct()
        .order_by(Playlist.created_at.desc())
    )
    return list(db.scalars(stmt).all())


def get_playlist(db: DbSession, playlist_id: str) -> Optional[Playlist]:
    return db.get(Playlist, playlist_id)


def create_playlist(db: DbSession, *, user: User, name: str, description: Optional[str], shared: bool = False) -> Playlist:
    clean = (name or "").strip()
    if not clean:
        raise PlaylistError("Playlist name is required")
    pl = Playlist(
        owner_user_id=user.id,
        name=clean,
        description=(description or "").strip() or None,
        is_shared=shared,
    )
    db.add(pl)
    db.commit()
    db.refresh(pl)
    return pl


def can_edit(pl: Playlist, user: User) -> bool:
    return pl.owner_user_id == user.id or any(row.user_id == user.id for row in pl.collaborators)


def add_collaborator(db: DbSession, pl: Playlist, username: str) -> Playlist:
    alias = username.strip().lower().removeprefix("@")
    user = db.scalar(select(User).where(User.username == alias))
    if user is None:
        raise PlaylistError("Usuario no encontrado")
    if user.id == pl.owner_user_id:
        raise PlaylistError("La persona propietaria ya tiene acceso")
    if not any(row.user_id == user.id for row in pl.collaborators):
        db.add(PlaylistCollaborator(playlist_id=pl.id, user_id=user.id))
    pl.is_shared = True
    db.commit()
    db.refresh(pl)
    return pl


def remove_collaborator(db: DbSession, pl: Playlist, username: str) -> Playlist:
    alias = username.strip().lower().removeprefix("@")
    user = db.scalar(select(User).where(User.username == alias))
    if user is None:
        raise PlaylistError("Usuario no encontrado")
    db.execute(
        delete(PlaylistCollaborator).where(
            PlaylistCollaborator.playlist_id == pl.id, PlaylistCollaborator.user_id == user.id
        )
    )
    db.commit()
    db.refresh(pl)
    return pl


def update_playlist(
    db: DbSession, pl: Playlist, *, name: Optional[str], description: Optional[str]
) -> Playlist:
    if name is not None:
        clean = name.strip()
        if not clean:
            raise PlaylistError("Playlist name cannot be empty")
        pl.name = clean
    if description is not None:
        pl.description = description.strip() or None
    pl.updated_at = utcnow()
    db.commit()
    db.refresh(pl)
    return pl


def delete_playlist(db: DbSession, pl: Playlist) -> None:
    db.delete(pl)
    db.commit()


def _next_position(db: DbSession, playlist_id: str) -> int:
    current = db.scalar(
        select(func.max(PlaylistTrack.position)).where(PlaylistTrack.playlist_id == playlist_id)
    )
    return (current or 0) + 1


def add_track(db: DbSession, pl: Playlist, track: Track) -> Playlist:
    exists = db.scalar(
        select(PlaylistTrack).where(
            PlaylistTrack.playlist_id == pl.id, PlaylistTrack.track_id == track.id
        )
    )
    if exists is None:
        db.add(
            PlaylistTrack(
                playlist_id=pl.id,
                track_id=track.id,
                position=_next_position(db, pl.id),
            )
        )
        pl.updated_at = utcnow()
        db.commit()
        db.refresh(pl)
    return pl


def remove_track(db: DbSession, pl: Playlist, track_id: str) -> Playlist:
    db.execute(
        delete(PlaylistTrack).where(
            PlaylistTrack.playlist_id == pl.id, PlaylistTrack.track_id == track_id
        )
    )
    pl.updated_at = utcnow()
    db.commit()
    db.refresh(pl)
    return pl


def reorder(db: DbSession, pl: Playlist, ordered_track_ids: List[str]) -> Playlist:
    rows = {item.track_id: item for item in pl.items}
    for index, track_id in enumerate(ordered_track_ids):
        if track_id in rows:
            rows[track_id].position = index
    pl.updated_at = utcnow()
    db.commit()
    db.refresh(pl)
    return pl


# ----------------------------- Favorites -----------------------------

def list_favorite_tracks(db: DbSession, user: User) -> List[Track]:
    stmt = (
        select(Track)
        .join(Favorite, Favorite.track_id == Track.id)
        .where(Favorite.user_id == user.id)
        .order_by(Favorite.created_at.desc())
    )
    return list(db.scalars(stmt).all())


def is_favorite(db: DbSession, user: User, track_id: str) -> bool:
    return (
        db.scalar(
            select(Favorite).where(Favorite.user_id == user.id, Favorite.track_id == track_id)
        )
        is not None
    )


def add_favorite(db: DbSession, user: User, track_id: str) -> None:
    if not is_favorite(db, user, track_id):
        db.add(Favorite(user_id=user.id, track_id=track_id))
        db.commit()


def remove_favorite(db: DbSession, user: User, track_id: str) -> None:
    db.execute(
        delete(Favorite).where(Favorite.user_id == user.id, Favorite.track_id == track_id)
    )
    db.commit()


# ------------------------------ History ------------------------------

def record_play(db: DbSession, user: User, track_id: str) -> History:
    entry = History(user_id=user.id, track_id=track_id, played_at=utcnow())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    _trim_history(db, user)
    return entry


def _trim_history(db: DbSession, user: User) -> None:
    stale_ids = list(
        db.scalars(
            select(History.id)
            .where(History.user_id == user.id)
            .order_by(History.played_at.desc())
            .offset(settings.history_max_entries)
        ).all()
    )
    if stale_ids:
        db.execute(delete(History).where(History.id.in_(stale_ids)))
        db.commit()


def list_history(db: DbSession, user: User, limit: int = 100) -> List[History]:
    stmt = (
        select(History)
        .where(History.user_id == user.id)
        .order_by(History.played_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt).all())
