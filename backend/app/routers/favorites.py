"""Favorites endpoints: /api/favorites/*"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DbSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services import library_service, playlist_service
from app.services.serializers import track_out

router = APIRouter(prefix="/api/favorites", tags=["favorites"])


@router.get("")
def list_favorites(user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    tracks = playlist_service.list_favorite_tracks(db, user)
    return [track_out(t) for t in tracks]


@router.post("/{track_id}", status_code=status.HTTP_204_NO_CONTENT)
def add_favorite(track_id: str, user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    if library_service.get_track(db, track_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Track not found")
    playlist_service.add_favorite(db, user, track_id)
    return None


@router.delete("/{track_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_favorite(track_id: str, user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    playlist_service.remove_favorite(db, user, track_id)
    return None
