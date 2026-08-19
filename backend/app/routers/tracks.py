"""Track metadata endpoint: GET /api/tracks/{id}"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DbSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.track import TrackOut
from app.services import library_service
from app.services.serializers import track_out

router = APIRouter(prefix="/api", tags=["tracks"])


@router.get("/tracks/{track_id}", response_model=TrackOut)
def get_track(track_id: str, _user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    track = library_service.get_track(db, track_id)
    if track is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Track not found")
    return track_out(track)
