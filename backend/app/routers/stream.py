"""Audio streaming proxy: GET /api/stream/{id}

The browser never talks to Navidrome directly. This endpoint authenticates the
user, resolves the opaque track id to an internal provider reference, and pipes
the upstream audio through — forwarding Range requests so seeking works. Upstream
credentials never leave the server.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session as DbSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services import library_service
from app.services.integrations import get_navidrome_client

router = APIRouter(prefix="/api", tags=["stream"])


@router.get("/stream/{track_id}")
async def stream(
    track_id: str,
    request: Request,
    _user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    track = library_service.get_track(db, track_id)
    if track is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Track not found")
    if track.status != "AVAILABLE" or not track.provider_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Track not available")

    client = get_navidrome_client()
    handle = await client.open_stream(track.provider_id, request.headers.get("range"))
    return StreamingResponse(
        handle.body,
        status_code=handle.status_code,
        headers=handle.headers,
        media_type=handle.headers.get("Content-Type", "audio/mpeg"),
    )
