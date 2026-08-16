"""Authentication endpoints: /api/auth/*"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session as DbSession

from app.config import settings
from app.core.cookies import clear_session_cookie, set_session_cookie
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import ChangePasswordInput, LoginInput
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
