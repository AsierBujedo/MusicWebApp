"""Music request endpoints for the current user: /api/requests/*"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session as DbSession

from app.core.permissions import ensure_owner_or_admin
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.request import CreateRequestInput, MusicRequestOut
from app.services import event_service, library_service, manual_import_service, request_service
from app.models.base import utcnow
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
    if req.status != "FAILED":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only failed requests can be imported manually")
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
