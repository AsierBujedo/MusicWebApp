"""Admin-only endpoints: /api/admin/*"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from app.database import get_db
from app.config import settings
from app.dependencies import get_current_admin, get_current_user, require_admin_feature
from app.core.cookies import clear_demo_admin_cookie, set_demo_admin_cookie, set_session_cookie
from app.core.features import require_feature
from app.core.features import ADMIN_FEATURES
from app.models.music_request import MusicRequest
from app.models.track import Track
from app.models.user import User, UserFeatureFlag
from app.schemas.user import CreateUserInput, UpdateUserInput, UpdateFeatureFlagsInput
from app.services import event_service, request_service, user_service
from app.services.integrations import (
    get_droppedneedle_client,
    get_navidrome_client,
    get_slskd_client,
)
from app.services.serializers import request_out, track_out, user_out
from app.services import auth_service

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/demo/users")
def demo_users(_admin: User = Depends(get_current_admin), db: DbSession = Depends(get_db)):
    return [user_out(user) for user in user_service.list_users(db) if user.id != _admin.id]


@router.post("/demo/{user_id}")
def start_demo(user_id: str, request: Request, response: Response, admin: User = Depends(get_current_admin), db: DbSession = Depends(get_db)):
    target = user_service.get_user(db, user_id)
    if target is None or not target.active:
        raise HTTPException(status_code=404, detail="Usuario no disponible")
    original = request.cookies.get(settings.session_cookie_name, "")
    if not original:
        raise HTTPException(status_code=401, detail="Sesión no válida")
    set_demo_admin_cookie(response, original)
    set_session_cookie(response, auth_service.create_session(db, target))
    return {"user": user_out(target), "impersonatedBy": admin.display_name}


@router.post("/demo/exit")
def exit_demo(request: Request, response: Response, db: DbSession = Depends(get_db)):
    original = request.cookies.get(f"{settings.session_cookie_name}_demo_admin", "")
    resolved = auth_service.resolve_session(db, original)
    if resolved is None or resolved[1].role != "ADMIN":
        clear_demo_admin_cookie(response)
        raise HTTPException(status_code=401, detail="La sesión administrativa ya no está disponible")
    set_session_cookie(response, original)
    clear_demo_admin_cookie(response)
    return user_out(resolved[1])


@router.get("/demo/status")
def demo_status(request: Request, user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    original = request.cookies.get(f"{settings.session_cookie_name}_demo_admin", "")
    resolved = auth_service.resolve_session(db, original)
    return {"active": resolved is not None, "adminName": resolved[1].display_name if resolved else None, "userId": user.id}


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
def all_tracks(_admin: User = Depends(require_admin_feature("admin.library")), db: DbSession = Depends(get_db)):
    """Return the complete playable library for the administrator view."""
    tracks = db.scalars(
        select(Track)
        .where(Track.status == "AVAILABLE")
        .order_by(Track.artist.asc(), Track.album.asc(), Track.title.asc())
    ).all()
    return [track_out(track) for track in tracks]


# ------------------------------- Users -------------------------------

@router.get("/users")
def list_users(_admin: User = Depends(require_admin_feature("admin.users")), db: DbSession = Depends(get_db)):
    return [user_out(u) for u in user_service.list_users(db)]


@router.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(
    payload: CreateUserInput, actor: User = Depends(require_admin_feature("admin.users")), db: DbSession = Depends(get_db)
):
    if actor.role != "ADMIN" and payload.role != "USER":
        raise HTTPException(status_code=403, detail="No puedes crear administradores")
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


@router.put("/users/{user_id}/features")
def update_feature_flags(user_id: str, payload: UpdateFeatureFlagsInput, admin: User = Depends(get_current_admin), db: DbSession = Depends(get_db)):
    user = user_service.get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == "ADMIN":
        raise HTTPException(status_code=400, detail="Los administradores ya tienen todas las funciones")
    requested = set(payload.feature_flags)
    if not requested.issubset(ADMIN_FEATURES):
        raise HTTPException(status_code=400, detail="Feature flag no válida")
    db.query(UserFeatureFlag).filter(UserFeatureFlag.user_id == user.id).delete()
    db.add_all([UserFeatureFlag(user_id=user.id, feature_key=key) for key in requested])
    db.commit(); db.refresh(user)
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
def all_requests(_admin: User = Depends(require_admin_feature("admin.requests")), db: DbSession = Depends(get_db)):
    reqs = request_service.list_requests(db)
    # Resolve requester display names in one pass.
    names = {u.id: u.display_name for u in user_service.list_users(db)}
    return [request_out(r, requested_by_name=names.get(r.requested_by)) for r in reqs]


@router.post("/requests/{request_id}/approve")
async def approve_request(
    request_id: str, _admin: User = Depends(require_admin_feature("admin.requests")), db: DbSession = Depends(get_db)
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
    request_id: str, _admin: User = Depends(require_admin_feature("admin.requests")), db: DbSession = Depends(get_db)
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
async def services(_admin: User = Depends(require_admin_feature("admin.services"))):
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


@router.post("/services/slskd/reset")
async def reset_slskd(_admin: User = Depends(get_current_admin)):
    """Destructive maintenance action: clear all slskd downloads and restart it."""
    slskd = get_slskd_client()
    try:
        result = await slskd.reset_download_queue()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="No se pudo vaciar ni reiniciar slskd") from exc
    finally:
        await slskd.aclose()
    return {"success": True, **result}
