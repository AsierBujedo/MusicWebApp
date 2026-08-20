"""Music request endpoints for the current user: /api/requests/*"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.core.permissions import ensure_owner_or_admin
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.request import CreateRequestInput, MusicRequestOut, YouTubeCandidateOut, YouTubeDownloadInput
from app.services import event_service, library_service, manual_import_service, request_service, youtube_fallback_service
from app.services.integrations import get_droppedneedle_client
from app.models.base import utcnow
from app.models.music_request import MusicRequest
from app.services.serializers import request_out

router = APIRouter(prefix="/api/requests", tags=["requests"])


@router.get("", response_model=list[MusicRequestOut])
def list_requests(user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    reqs = request_service.list_requests(db, user=user)
    return [request_out(r, requested_by_name=user.display_name) for r in reqs]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=MusicRequestOut)
async def create_request(
    payload: CreateRequestInput,
    user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    track = library_service.get_track(db, payload.track_id)
    if track is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Track not found")
    if track.status == "AVAILABLE":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Track already available")

    req = request_service.create_request(db, user=user, type_=payload.type, track=track)
    # Reflect the pending state on any open search views.
    await event_service.emit_track_updated(
        track_id=track.id, status=track.status, progress=None, audience_user_ids={user.id}
    )
    return request_out(req, requested_by_name=user.display_name)


@router.get("/{request_id}", response_model=MusicRequestOut)
def get_request(request_id: str, user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    req = request_service.get_request(db, request_id)
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    ensure_owner_or_admin(user, req.requested_by)
    return request_out(req)


@router.delete("/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_request(request_id: str, user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    req = request_service.get_request(db, request_id)
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    ensure_owner_or_admin(user, req.requested_by)
    request_service.delete_request(db, req)
    return None


@router.post("/{request_id}/retry", response_model=MusicRequestOut)
async def retry_request(request_id: str, user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    req = request_service.get_request(db, request_id)
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    ensure_owner_or_admin(user, req.requested_by)
    try:
        req = request_service.retry(db, req)
    except request_service.RequestError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    await event_service.emit_request_updated(
        request_id=req.id, status=req.status, progress=req.progress, owner_user_id=req.requested_by
    )
    return request_out(req, requested_by_name=user.display_name)


async def _cancel_active_request(req: MusicRequest, db: DbSession) -> None:
    """Cancel a queued or active remote task, then remove its local request."""

    # Once DroppedNeedle has a task ID, it owns live slskd transfers. Do not
    # remove Resonar's row unless DroppedNeedle confirms that cancellation.
    if req.external_id:
        droppedneedle = get_droppedneedle_client()
        try:
            cancelled = await droppedneedle.cancel(req.external_id)
        finally:
            await droppedneedle.aclose()
        if not cancelled:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Remote download could not be cancelled")
    elif req.status != "APPROVED":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Remote task is not ready to cancel")

    track_id, owner_user_id = req.track_id, req.requested_by
    request_service.delete_request(db, req)
    track = library_service.get_track(db, track_id)
    if track is not None:
        await event_service.emit_track_updated(
            track_id=track.id, status=track.status, progress=None, audience_user_ids={owner_user_id}
        )
    return None


@router.post("/{request_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_active_request(
    request_id: str, user: User = Depends(get_current_user), db: DbSession = Depends(get_db)
):
    req = request_service.get_request(db, request_id)
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    ensure_owner_or_admin(user, req.requested_by)
    if req.status not in {"APPROVED", "SEARCHING", "DOWNLOADING"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only approved or active requests can be cancelled")
    await _cancel_active_request(req, db)


@router.post("/track/{track_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_active_track_request(
    track_id: str, user: User = Depends(get_current_user), db: DbSession = Depends(get_db)
):
    """Cancel the current user's active request for a track (or any request for admins)."""
    statement = (
        select(MusicRequest)
        .where(
            MusicRequest.track_id == track_id,
            MusicRequest.status.in_({"APPROVED", "SEARCHING", "DOWNLOADING"}),
        )
        .order_by(MusicRequest.created_at.desc())
    )
    if user.role != "ADMIN":
        statement = statement.where(MusicRequest.requested_by == user.id)
    req = db.scalar(statement)
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active request found for track")
    await _cancel_active_request(req, db)


@router.post("/{request_id}/upload", response_model=MusicRequestOut)
async def upload_failed_request(
    request_id: str,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    """Import a user-supplied MP3/FLAC for a failed request.

    The uploaded file is treated purely as audio. Its own tags and artwork are
    removed and replaced with the metadata already stored by Resonar.
    """
    req = request_service.get_request(db, request_id)
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    ensure_owner_or_admin(user, req.requested_by)
    if req.status not in {"FAILED", "REJECTED"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only unsuccessful requests can be imported manually")
    track = library_service.get_track(db, req.track_id)
    if track is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Track not found")

    destination = await manual_import_service.import_audio(upload=file, track=track)
    track.provider = "manual"
    track.provider_id = None
    track.file_reference = str(destination)
    track.cover = f"/api/covers/{track.id}"
    track.status = "AVAILABLE"
    track.available = True
    track.progress = None
    track.updated_at = utcnow()
    req.cover = track.cover
    try:
        req = request_service.transition(db, req, "AVAILABLE", error_message=None)
    except request_service.RequestError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    await event_service.emit_track_updated(
        track_id=track.id, status=track.status, progress=None, audience_user_ids={req.requested_by}
    )
    await event_service.emit_request_updated(request_id=req.id, status=req.status, progress=req.progress, owner_user_id=req.requested_by)
    return request_out(req, requested_by_name=user.display_name)


def _failed_request_track(request_id: str, user: User, db: DbSession):
    req = request_service.get_request(db, request_id)
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    ensure_owner_or_admin(user, req.requested_by)
    if req.status not in {"FAILED", "REJECTED"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="YouTube fallback is only available for unsuccessful requests")
    track = library_service.get_track(db, req.track_id)
    if track is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Track not found")
    return req, track


@router.get("/{request_id}/youtube-candidates", response_model=list[YouTubeCandidateOut])
async def youtube_candidates(request_id: str, user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    _req, track = _failed_request_track(request_id, user, db)
    return [
        YouTubeCandidateOut(video_id=item.video_id, title=item.title, channel=item.channel, duration=item.duration)
        for item in await youtube_fallback_service.candidates(track)
    ]


@router.post("/{request_id}/youtube-download", response_model=MusicRequestOut)
async def youtube_download(
    request_id: str,
    payload: YouTubeDownloadInput,
    user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    req, track = _failed_request_track(request_id, user, db)
    destination = await youtube_fallback_service.download_selected(video_id=payload.video_id, track=track)
    track.provider = "manual"
    track.provider_id = None
    track.file_reference = str(destination)
    track.cover = f"/api/covers/{track.id}"
    track.status = "AVAILABLE"
    track.available = True
    track.progress = None
    track.updated_at = utcnow()
    req.cover = track.cover
    req = request_service.transition(db, req, "AVAILABLE", error_message=None)
    await event_service.emit_track_updated(
        track_id=track.id, status=track.status, progress=None, audience_user_ids={req.requested_by}
    )
    await event_service.emit_request_updated(request_id=req.id, status=req.status, progress=req.progress, owner_user_id=req.requested_by)
    return request_out(req, requested_by_name=user.display_name)
