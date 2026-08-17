"""Music request endpoints for the current user: /api/requests/*"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DbSession

from app.core.permissions import ensure_owner_or_admin
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.request import CreateRequestInput
from app.services import event_service, library_service, request_service
from app.services.integrations import get_droppedneedle_client
from app.services.serializers import request_out

router = APIRouter(prefix="/api/requests", tags=["requests"])


@router.get("")
def list_requests(user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    reqs = request_service.list_requests(db, user=user)
    return [request_out(r, requested_by_name=user.display_name) for r in reqs]


@router.post("", status_code=status.HTTP_201_CREATED)
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

    # Submit the acquisition to DroppedNeedle (keyed by MusicBrainz id). The
    # returned external id lets the worker reconcile progress later. Failure to
    # submit does not lose the request; the worker retries via the PENDING state.
    if req.musicbrainz_id is None and track.musicbrainz_id:
        req.musicbrainz_id = track.musicbrainz_id
    dn = get_droppedneedle_client()
    try:
        result = await dn.request(
            type=req.type, title=req.title, artist=req.artist, musicbrainz_id=track.musicbrainz_id
        )
        if result.get("accepted") and result.get("external_id"):
            req.external_id = str(result["external_id"])
        db.commit()
        db.refresh(req)
    finally:
        await dn.aclose()

    # Reflect the pending state on any open search views.
    await event_service.emit_track_updated(
        track_id=track.id, status=track.status, progress=None, audience_user_ids=None
    )
    return request_out(req, requested_by_name=user.display_name)


@router.get("/{request_id}")
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


@router.post("/{request_id}/retry")
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
