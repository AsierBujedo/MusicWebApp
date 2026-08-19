"""Admin-only endpoints: /api/admin/*"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from app.database import get_db
from app.dependencies import get_current_admin
from app.models.music_request import MusicRequest
from app.models.track import Track
from app.models.user import User
from app.schemas.user import CreateUserInput, UpdateUserInput
from app.services import event_service, request_service, user_service
from app.services.integrations import (
    get_droppedneedle_client,
    get_navidrome_client,
    get_slskd_client,
)
from app.services.serializers import request_out, track_out, user_out

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ------------------------------- Stats -------------------------------

@router.get("/stats")
def stats(_admin: User = Depends(get_current_admin), db: DbSession = Depends(get_db)):
    users = db.scalar(select(func.count()).select_from(User)) or 0
    requests = db.scalar(select(func.count()).select_from(MusicRequest)) or 0
    downloads = (
        db.scalar(
            select(func.count()).select_from(MusicRequest).where(MusicRequest.status == "AVAILABLE")
        )
        or 0
    )
    available_tracks = (
        db.scalar(select(func.count()).select_from(Track).where(Track.status == "AVAILABLE")) or 0
    )
    return {
        "users": users,
        "requests": requests,
        "downloads": downloads,
        "availableTracks": available_tracks,
    }


# ------------------------------ Library ------------------------------


@router.get("/tracks")
def all_tracks(_admin: User = Depends(get_current_admin), db: DbSession = Depends(get_db)):
    """Return the complete playable library for the administrator view."""
    tracks = db.scalars(
        select(Track)
        .where(Track.status == "AVAILABLE")
        .order_by(Track.artist.asc(), Track.album.asc(), Track.title.asc())
    ).all()
    return [track_out(track) for track in tracks]


# ------------------------------- Users -------------------------------

@router.get("/users")
def list_users(_admin: User = Depends(get_current_admin), db: DbSession = Depends(get_db)):
    return [user_out(u) for u in user_service.list_users(db)]


@router.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(
    payload: CreateUserInput, _admin: User = Depends(get_current_admin), db: DbSession = Depends(get_db)
):
    try:
        user = user_service.create_user(
            db,
            username=payload.username,
            display_name=payload.display_name,
            email=payload.email,
            role=payload.role,
            password=payload.password,
            auto_approve_requests=payload.auto_approve_requests,
        )
    except user_service.UserError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return user_out(user)


@router.patch("/users/{user_id}")
def update_user(
    user_id: str,
    payload: UpdateUserInput,
    admin: User = Depends(get_current_admin),
    db: DbSession = Depends(get_db),
):
    user = user_service.get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    # Guard against removing the last admin or self-demotion locking everyone out.
    demoting = (payload.role == "USER" and user.role == "ADMIN") or (payload.active is False and user.role == "ADMIN")
    if demoting and user_service.count_admins(db) <= 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot remove the last admin")
    user = user_service.update_user(
        db,
        user,
        display_name=payload.display_name,
        email=payload.email,
        avatar=payload.avatar,
        role=payload.role,
        auto_approve_requests=payload.auto_approve_requests,
        active=payload.active,
    )
    return user_out(user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: str, admin: User = Depends(get_current_admin), db: DbSession = Depends(get_db)
):
    user = user_service.get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot delete your own account")
    if user.role == "ADMIN" and user_service.count_admins(db) <= 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete the last admin")
    user_service.delete_user(db, user)
    return None


# ------------------------------ Requests ------------------------------

@router.get("/requests")
def all_requests(_admin: User = Depends(get_current_admin), db: DbSession = Depends(get_db)):
    reqs = request_service.list_requests(db)
    # Resolve requester display names in one pass.
    names = {u.id: u.display_name for u in user_service.list_users(db)}
    return [request_out(r, requested_by_name=names.get(r.requested_by)) for r in reqs]


@router.post("/requests/{request_id}/approve")
async def approve_request(
    request_id: str, _admin: User = Depends(get_current_admin), db: DbSession = Depends(get_db)
):
    req = request_service.get_request(db, request_id)
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    try:
        req = request_service.transition(db, req, "APPROVED")
    except request_service.RequestError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    await event_service.emit_request_updated(
        request_id=req.id, status=req.status, progress=req.progress, owner_user_id=req.requested_by
    )
    return request_out(req)


@router.post("/requests/{request_id}/reject")
async def reject_request(
    request_id: str, _admin: User = Depends(get_current_admin), db: DbSession = Depends(get_db)
):
    req = request_service.get_request(db, request_id)
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    try:
        req = request_service.transition(db, req, "REJECTED")
    except request_service.RequestError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    await event_service.emit_request_updated(
        request_id=req.id, status=req.status, progress=req.progress, owner_user_id=req.requested_by
    )
    return request_out(req)


# ------------------------------ Services ------------------------------

@router.get("/services")
async def services(_admin: User = Depends(get_current_admin)):
    navidrome = get_navidrome_client()
    droppedneedle = get_droppedneedle_client()
    slskd = get_slskd_client()

    (nav_status, nav_detail), (dn_status, dn_detail), (sl_status, sl_detail) = await asyncio.gather(
        navidrome.health(), droppedneedle.health(), slskd.health()
    )
    # Best-effort cleanup of any real HTTP clients.
    for client in (navidrome, droppedneedle, slskd):
        await client.aclose()

    return [
        {"name": "Navidrome", "key": "navidrome", "status": nav_status, "detail": nav_detail},
        {"name": "DroppedNeedle", "key": "droppedneedle", "status": dn_status, "detail": dn_detail},
        {"name": "slskd", "key": "slskd", "status": sl_status, "detail": sl_detail},
    ]
