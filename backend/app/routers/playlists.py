"""Playlist endpoints: /api/playlists/*"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session as DbSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.playlist import (
    AddTrackInput,
    AddCollaboratorInput,
    CreatePlaylistInput,
    ReorderInput,
    UpdatePlaylistInput,
    PlaylistOut,
)
from app.services import library_service, playlist_service
from app.services.serializers import playlist_out

router = APIRouter(prefix="/api/playlists", tags=["playlists"])


def _load_editable(db: DbSession, playlist_id: str, user: User):
    pl = playlist_service.get_playlist(db, playlist_id)
    if pl is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playlist not found")
    if not playlist_service.can_edit(pl, user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playlist not found")
    return pl


@router.get("", response_model=list[PlaylistOut])
def list_playlists(user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    return [playlist_out(db, pl) for pl in playlist_service.list_playlists(db, user)]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=PlaylistOut)
def create_playlist(
    payload: CreatePlaylistInput, user: User = Depends(get_current_user), db: DbSession = Depends(get_db)
):
    try:
        pl = playlist_service.create_playlist(db, user=user, name=payload.name, description=payload.description, shared=payload.shared)
    except playlist_service.PlaylistError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return playlist_out(db, pl)


@router.get("/{playlist_id}", response_model=PlaylistOut)
def get_playlist(playlist_id: str, user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    pl = _load_editable(db, playlist_id, user)
    return playlist_out(db, pl)


@router.patch("/{playlist_id}", response_model=PlaylistOut)
def update_playlist(
    playlist_id: str,
    payload: UpdatePlaylistInput,
    user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    pl = _load_editable(db, playlist_id, user)
    try:
        pl = playlist_service.update_playlist(db, pl, name=payload.name, description=payload.description)
    except playlist_service.PlaylistError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return playlist_out(db, pl)


@router.delete("/{playlist_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_playlist(playlist_id: str, user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    pl = _load_editable(db, playlist_id, user)
    playlist_service.delete_playlist(db, pl)
    return None


@router.post("/{playlist_id}/tracks", response_model=PlaylistOut)
def add_track(
    playlist_id: str,
    payload: AddTrackInput,
    user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    pl = _load_editable(db, playlist_id, user)
    track = library_service.get_track(db, payload.track_id)
    if track is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Track not found")
    pl = playlist_service.add_track(db, pl, track)
    return playlist_out(db, pl)


@router.delete("/{playlist_id}/tracks/{track_id}", response_model=PlaylistOut)
def remove_track(
    playlist_id: str,
    track_id: str,
    user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    pl = _load_editable(db, playlist_id, user)
    pl = playlist_service.remove_track(db, pl, track_id)
    return playlist_out(db, pl)


@router.post("/{playlist_id}/collaborators", response_model=PlaylistOut)
def add_collaborator(playlist_id: str, payload: AddCollaboratorInput, user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    pl = _load_editable(db, playlist_id, user)
    try:
        pl = playlist_service.add_collaborator(db, pl, payload.username)
    except playlist_service.PlaylistError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return playlist_out(db, pl)


@router.post("/{playlist_id}/cover", response_model=PlaylistOut)
async def upload_cover(playlist_id: str, file: UploadFile = File(...), user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    pl = _load_editable(db, playlist_id, user)
    if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=400, detail="La portada debe ser JPG, PNG o WebP")
    payload = await file.read()
    if len(payload) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="La portada supera 5 MB")
    ext = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}[file.content_type]
    directory = Path("data/playlist-covers")
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{pl.id}.{ext}"
    target.write_bytes(payload)
    pl.cover = f"/api/playlists/{pl.id}/cover"
    pl.custom_cover_path = str(target)
    db.commit()
    db.refresh(pl)
    return playlist_out(db, pl)


@router.get("/{playlist_id}/cover")
def playlist_cover(playlist_id: str, user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    pl = _load_editable(db, playlist_id, user)
    if pl.custom_cover_path and os.path.isfile(pl.custom_cover_path):
        return FileResponse(pl.custom_cover_path, headers={"Cache-Control": "private, max-age=86400"})
    covers = [item.track.cover or "" for item in pl.items[:4]]
    cells = "".join(f'<image href="{cover}" x="{(i % 2) * 50}" y="{(i // 2) * 50}" width="50" height="50" preserveAspectRatio="xMidYMid slice"/>' for i, cover in enumerate(covers) if cover)
    if not cells:
        cells = '<rect width="100" height="100" fill="#252735"/>'
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">{cells}</svg>'
    return Response(svg, media_type="image/svg+xml", headers={"Cache-Control": "private, max-age=300"})


@router.post("/{playlist_id}/reorder", response_model=PlaylistOut)
def reorder(
    playlist_id: str,
    payload: ReorderInput,
    user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    pl = _load_editable(db, playlist_id, user)
    pl = playlist_service.reorder(db, pl, payload.track_ids)
    return playlist_out(db, pl)
