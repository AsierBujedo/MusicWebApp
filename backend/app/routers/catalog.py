"""Artist and album catalogue views backed by DroppedNeedle/MusicBrainz."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session as DbSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services import library_service
from app.services.integrations import get_droppedneedle_client
from app.services.integrations.base import ExternalTrack
from app.services.serializers import track_out

router = APIRouter(prefix="/api/catalog", tags=["catalog"])


def _release_out(item: dict) -> dict:
    release_id = str(item.get("id") or item.get("musicbrainz_id") or "")
    return {
        "id": release_id,
        "title": str(item.get("title") or "Álbum sin título"),
        "year": item.get("year"),
        "inLibrary": bool(item.get("in_library")),
        "requested": bool(item.get("requested")),
        "cover": f"/api/covers/release-group/{release_id}" if release_id else None,
    }


def _allow_bulk_requests(user: User) -> None:
    if user.role == "ADMIN" or user.auto_approve_requests:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Necesitas autoaprobación o ser administrador para solicitar álbumes completos.",
    )


@router.get("/artists/{artist_id}")
async def get_artist(artist_id: str, name: str | None = Query(default=None), _user: User = Depends(get_current_user)):
    client = get_droppedneedle_client()
    try:
        data = await client.get_artist_catalog(artist_id, name)
    finally:
        await client.aclose()
    if not data:
        raise HTTPException(status_code=404, detail="Artista no encontrado")
    albums = [_release_out(x) for x in data.get("albums", []) if isinstance(x, dict)]
    eps = [_release_out(x) for x in data.get("eps", []) if isinstance(x, dict)]
    return {
        "id": str(data.get("musicbrainz_id") or artist_id),
        "name": str(data.get("name") or "Artista"),
        "image": data.get("image") or data.get("thumb_url"),
        "albums": albums,
        "eps": eps,
        "singlesCount": len(data.get("singles", [])),
    }


@router.get("/albums/{album_id}")
async def get_album(album_id: str, artist: str | None = Query(default=None), title: str | None = Query(default=None), _user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    client = get_droppedneedle_client()
    try:
        data = await client.get_album_catalog(album_id, artist, title)
    finally:
        await client.aclose()
    if not data:
        raise HTTPException(status_code=404, detail="Álbum no encontrado")
    artist = str(data.get("artist_name") or "Artista desconocido")
    artist_id = data.get("artist_id")
    cover = data.get("cover_url") or data.get("album_thumb_url") or f"/api/covers/release-group/{album_id}"
    tracks = []
    for item in data.get("tracks", []):
        if not isinstance(item, dict) or not item.get("recording_id"):
            continue
        ext = ExternalTrack(
            provider="droppedneedle", provider_id=str(item["recording_id"]), title=str(item.get("title") or "Canción sin título"),
            artist=artist, artist_id=str(artist_id) if artist_id else None, album=str(data.get("title") or ""),
            album_id=album_id, year=data.get("year"), duration=item.get("length"), cover=cover,
            available=False, status="REQUESTABLE", metadata={"release_mbid": data.get("selected_release_mbid")} if data.get("selected_release_mbid") else None,
        )
        tracks.append(track_out(library_service.upsert_external_track(db, ext)))
    return {"id": str(data.get("musicbrainz_id") or album_id), "title": data.get("title") or "Álbum", "artist": artist,
            "artistId": artist_id, "year": data.get("year"), "cover": cover, "inLibrary": bool(data.get("in_library")), "tracks": tracks}


@router.post("/albums/{album_id}/request")
async def request_album(album_id: str, user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    _allow_bulk_requests(user)
    client = get_droppedneedle_client()
    try:
        album = await client.get_album_catalog(album_id)
        if not album:
            raise HTTPException(status_code=404, detail="Álbum no encontrado")
        result = await client.request_album(musicbrainz_id=album_id, artist=str(album.get("artist_name") or "Unknown"), album=str(album.get("title") or "Unknown"), year=album.get("year"), artist_mbid=album.get("artist_id"))
    finally:
        await client.aclose()
    if not result.get("success"):
        raise HTTPException(status_code=502, detail="DroppedNeedle no aceptó la solicitud")
    return result


@router.post("/artists/{artist_id}/request")
async def request_artist(artist_id: str, user: User = Depends(get_current_user)):
    _allow_bulk_requests(user)
    client = get_droppedneedle_client()
    try:
        artist = await client.get_artist_catalog(artist_id)
        if not artist:
            raise HTTPException(status_code=404, detail="Artista no encontrado")
        releases = [x for x in [*artist.get("albums", []), *artist.get("eps", [])] if isinstance(x, dict) and x.get("id") and not x.get("in_library")]
        items = [{"musicbrainz_id": str(x["id"]), "artist_name": str(artist.get("name") or "Unknown"), "album_title": str(x.get("title") or "Unknown"), "year": x.get("year"), "artist_mbid": artist_id} for x in releases]
        if not items:
            return {"success": True, "requested": 0, "skipped": 0, "message": "No hay álbumes ni EPs pendientes"}
        result = await client.request_albums(items)
    finally:
        await client.aclose()
    if not result.get("success"):
        raise HTTPException(status_code=502, detail="DroppedNeedle no aceptó la discografía")
    return result
