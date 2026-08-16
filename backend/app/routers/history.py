"""Listening-history endpoints: /api/history"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DbSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.history import RecordPlayInput
from app.services import library_service, playlist_service
from app.services.serializers import history_out

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("")
def list_history(user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    entries = playlist_service.list_history(db, user)
    return [out for out in (history_out(e) for e in entries) if out is not None]


@router.post("", status_code=status.HTTP_204_NO_CONTENT)
def record_play(
    payload: RecordPlayInput, user: User = Depends(get_current_user), db: DbSession = Depends(get_db)
):
    if library_service.get_track(db, payload.track_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Track not found")
    playlist_service.record_play(db, user, payload.track_id)
    return None
