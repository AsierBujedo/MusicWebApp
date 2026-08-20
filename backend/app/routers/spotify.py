"""Spotify playlist import endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.spotify_connection import SpotifyConnection
from app.models.user import User
from app.schemas.spotify import SpotifyImportInput, SpotifyImportOut, SpotifyPlaylistOut, SpotifyStatusOut
from app.services import spotify_service

router = APIRouter(prefix="/api/integrations/spotify", tags=["spotify"])


@router.get("/status", response_model=SpotifyStatusOut)
def spotify_status(user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    connection = db.scalar(select(SpotifyConnection).where(SpotifyConnection.user_id == user.id))
    return SpotifyStatusOut(
        configured=spotify_service.configured(),
        connected=connection is not None,
        display_name=connection.spotify_user_id if connection else None,
    )


@router.post("/connect")
def connect_spotify(user: User = Depends(get_current_user)):
    try:
        return {"authorizationUrl": spotify_service.authorization_url(user)}
    except spotify_service.SpotifyError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.get("/callback", include_in_schema=False)
async def spotify_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    if error or not code or not state:
        return RedirectResponse("/profile?spotify=denied", status_code=status.HTTP_303_SEE_OTHER)
    try:
        await spotify_service.complete_connection(db, user, code=code, state=state)
    except spotify_service.SpotifyError:
        return RedirectResponse("/profile?spotify=error", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse("/profile?spotify=connected", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/playlists", response_model=list[SpotifyPlaylistOut])
async def spotify_playlists(user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    try:
        return [SpotifyPlaylistOut(**item) for item in await spotify_service.list_playlists(db, user)]
    except spotify_service.SpotifyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/import", response_model=SpotifyImportOut)
async def import_spotify_playlists(
    payload: SpotifyImportInput, user: User = Depends(get_current_user), db: DbSession = Depends(get_db)
):
    try:
        playlists, imported_tracks, matched_tracks = await spotify_service.import_playlists(db, user, payload.playlist_ids)
    except spotify_service.SpotifyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return SpotifyImportOut(
        imported_playlists=len(playlists), imported_tracks=imported_tracks, matched_tracks=matched_tracks,
        playlists=[playlist.id for playlist in playlists],
    )
