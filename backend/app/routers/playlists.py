"""Playlist endpoints: /api/playlists/*"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DbSession

from app.core.permissions import ensure_owner_or_admin
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.playlist import (
    AddTrackInput,
    CreatePlaylistInput,
    ReorderInput,
    UpdatePlaylistInput,
)
from app.services import library_service, playlist_service
from app.services.serializers import playlist_out

router = APIRouter(prefix="/api/playlists", tags=["playlists"])


def _load_owned(db: DbSession, playlist_id: str, user: User):
    pl = playlist_service.get_playlist(db, playlist_id)
    if pl is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playlist not found")
    ensure_owner_or_admin(user, pl.owner_user_id)
    return pl


@router.get("")
def list_playlists(user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    return [playlist_out(db, pl) for pl in playlist_service.list_playlists(db, user)]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_playlist(
    payload: CreatePlaylistInput, user: User = Depends(get_current_user), db: DbSession = Depends(get_db)
):
    try:
        pl = playlist_service.create_playlist(db, user=user, name=payload.name, description=payload.description)
    except playlist_service.PlaylistError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return playlist_out(db, pl)


@router.get("/{playlist_id}")
def get_playlist(playlist_id: str, user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    pl = _load_owned(db, playlist_id, user)
    return playlist_out(db, pl)


@router.patch("/{playlist_id}")
def update_playlist(
    playlist_id: str,
    payload: UpdatePlaylistInput,
    user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    pl = _load_owned(db, playlist_id, user)
    try:
        pl = playlist_service.update_playlist(db, pl, name=payload.name, description=payload.description)
    except playlist_service.PlaylistError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return playlist_out(db, pl)


@router.delete("/{playlist_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_playlist(playlist_id: str, user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    pl = _load_owned(db, playlist_id, user)
    playlist_service.delete_playlist(db, pl)
    return None


@router.post("/{playlist_id}/tracks")
def add_track(
    playlist_id: str,
    payload: AddTrackInput,
    user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    pl = _load_owned(db, playlist_id, user)
    track = library_service.get_track(db, payload.track_id)
    if track is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Track not found")
    pl = playlist_service.add_track(db, pl, track)
    return playlist_out(db, pl)


@router.delete("/{playlist_id}/tracks/{track_id}")
def remove_track(
    playlist_id: str,
    track_id: str,
    user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    pl = _load_owned(db, playlist_id, user)
    pl = playlist_service.remove_track(db, pl, track_id)
    return playlist_out(db, pl)


@router.post("/{playlist_id}/reorder")
def reorder(
    playlist_id: str,
    payload: ReorderInput,
    user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    pl = _load_owned(db, playlist_id, user)
    pl = playlist_service.reorder(db, pl, payload.track_ids)
    return playlist_out(db, pl)
