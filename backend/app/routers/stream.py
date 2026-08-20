"""Audio streaming proxy: GET /api/stream/{id}

The browser never talks to Navidrome directly. This endpoint authenticates the
user, resolves the opaque track id to an internal provider reference, and pipes
the upstream audio through — forwarding Range requests so seeking works. Upstream
credentials never leave the server.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from starlette.background import BackgroundTask
from fastapi.responses import FileResponse, StreamingResponse
from pathlib import Path
from sqlalchemy.orm import Session as DbSession

from app.database import get_db
from app.config import settings
from app.dependencies import get_current_user
from app.models.user import User
from app.services import library_service, manual_import_service
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
    if track.status != "AVAILABLE":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Track not available")

    # A manually supplied file is playable immediately; Navidrome will also
    # index the shared library shortly afterwards. Resolve and validate the
    # path so a database value can never expose a file outside the library.
    if track.provider == "manual" and track.file_reference:
        library_root = Path(settings.music_library_path).resolve()
        source = Path(track.file_reference).resolve()
        if not source.is_file() or not source.is_relative_to(library_root):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manual audio file not found")
        actual_duration = manual_import_service.duration_seconds(source)
        if actual_duration and actual_duration != track.duration:
            track.duration = actual_duration
            db.commit()
        media_type = "audio/flac" if source.suffix.lower() == ".flac" else "audio/mpeg"
        return FileResponse(source, media_type=media_type)

    if not track.provider_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Track not available")

    client = get_navidrome_client()
    provider_id = track.provider_id
    # A catalogue result can say it exists locally just before Navidrome's scan
    # catches up. Resolve it here rather than sending a DroppedNeedle ID to the
    # Subsonic stream endpoint.
    if track.provider != "navidrome":
        found = await client.search(f"{track.artist} {track.title}", limit=10)
        match = next(
            (
                item for item in found.tracks
                if item.title.casefold() == track.title.casefold()
                and item.artist.casefold() == track.artist.casefold()
            ),
            None,
        )
        if match is None:
            await client.aclose()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Track is still indexing")
        track.provider = "navidrome"
        track.provider_id = match.provider_id
        track.available = True
        db.commit()
        provider_id = match.provider_id
    handle = await client.open_stream(provider_id, request.headers.get("range"))
    return StreamingResponse(
        handle.body,
        status_code=handle.status_code,
        headers=handle.headers,
        media_type=handle.headers.get("Content-Type", "audio/mpeg"),
        background=BackgroundTask(client.aclose),
    )
