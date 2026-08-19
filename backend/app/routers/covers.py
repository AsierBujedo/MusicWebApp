"""Authenticated cover-art proxy for Navidrome."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask
from sqlalchemy.orm import Session as DbSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services import library_service
from app.services.integrations import get_navidrome_client

router = APIRouter(prefix="/api", tags=["covers"])


@router.get("/covers/{track_id}")
async def cover(
    track_id: str,
    _user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    track = library_service.get_track(db, track_id)
    if track is None or track.provider != "navidrome" or not track.provider_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cover not found")

    navidrome = get_navidrome_client()
    try:
        song = await navidrome.get_track(track.provider_id)
        if song is None or not song.cover_id:
            await navidrome.aclose()
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cover not found")
        handle = await navidrome.open_cover(song.cover_id)
        if handle.status_code >= 400:
            await navidrome.aclose()
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cover not found")
    except HTTPException:
        raise
    except Exception:
        await navidrome.aclose()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Cover service unavailable")

    return StreamingResponse(
        handle.body,
        status_code=handle.status_code,
        headers=handle.headers,
        media_type=handle.headers.get("Content-Type", "image/jpeg"),
        background=BackgroundTask(navidrome.aclose),
    )
