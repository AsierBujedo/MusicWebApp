"""Authentication endpoints: /api/auth/*"""
from __future__ import annotations

from pathlib import Path
import time
from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session as DbSession

from app.config import settings
from app.core.cookies import clear_session_cookie, set_session_cookie
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import ChangePasswordInput, LoginInput, UpdateEmailInput
from app.services import auth_service
from app.services.serializers import user_out

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
def login(payload: LoginInput, response: Response, db: DbSession = Depends(get_db)):
    try:
        user = auth_service.authenticate(db, payload.username, payload.password)
    except auth_service.AuthError:
        # Deliberately vague: do not reveal whether user/password was wrong.
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = auth_service.create_session(db, user)
    set_session_cookie(response, token)
    return user_out(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: DbSession = Depends(get_db)):
    raw_token = request.cookies.get(settings.session_cookie_name, "")
    auth_service.revoke_session(db, raw_token)
    clear_session_cookie(response)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return user_out(user)

@router.post("/avatar")
async def upload_avatar(file: UploadFile = File(...), user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    if file.content_type not in {"image/jpeg", "image/png", "image/webp"}: raise HTTPException(400, "Usa JPG, PNG o WebP")
    payload = await file.read()
    if len(payload) > 5 * 1024 * 1024: raise HTTPException(400, "La foto supera 5 MB")
    ext = {"image/jpeg":"jpg", "image/png":"png", "image/webp":"webp"}[file.content_type]
    directory = Path("data/avatars"); directory.mkdir(parents=True, exist_ok=True)
    # The extension can change between uploads. Remove the old file first so
    # the avatar endpoint never serves a stale JPG/PNG/WebP chosen by glob().
    for old_avatar in directory.glob(f"{user.id}.*"):
        if old_avatar.is_file():
            old_avatar.unlink()
    target = directory / f"{user.id}.{ext}"; target.write_bytes(payload)
    user.avatar = f"/api/auth/avatars/{user.id}?v={int(time.time() * 1000)}"; db.commit()
    return user_out(user)

@router.get("/avatars/{user_id}")
def avatar(user_id: str, _user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    target = next((p for p in Path("data/avatars").glob(f"{user_id}.*") if p.is_file()), None)
    if target is None: raise HTTPException(404, "Avatar not found")
    return FileResponse(target, headers={"Cache-Control": "private, no-store"})


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: ChangePasswordInput,
    user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    try:
        auth_service.change_password(db, user, payload.current_password, payload.new_password)
    except auth_service.AuthError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password incorrect")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/profile")
def update_profile(payload: UpdateEmailInput, user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    try:
        user = auth_service.update_email(db, user, payload.email)
    except auth_service.AuthError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email no válido o ya en uso")
    return user_out(user)
