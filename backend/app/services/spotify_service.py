"""Spotify OAuth and playlist metadata import.

Spotify is a metadata source only. Tokens are encrypted at rest and audio never
passes through this service.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import secrets
from datetime import timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx
from itsdangerous import BadData, URLSafeTimedSerializer
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from app.config import settings
from app.core.security import decrypt_secret, encrypt_secret
from app.models.base import utcnow
from app.models.playlist import Playlist
from app.models.spotify_connection import SpotifyConnection
from app.models.track import Track
from app.models.user import User
from app.services import library_service, playlist_service
from app.services.integrations.base import ExternalTrack

logger = logging.getLogger(__name__)
_AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
_TOKEN_URL = "https://accounts.spotify.com/api/token"
_API_URL = "https://api.spotify.com/v1"
_SCOPES = "playlist-read-private playlist-read-collaborative"
_STATE_MAX_AGE_SECONDS = 600
_MUSICBRAINZ_URL = "https://musicbrainz.org/ws/2/recording/"
_MUSICBRAINZ_USER_AGENT = "Resonar/1.0 (self-hosted Spotify playlist import)"
_mb_lock = asyncio.Lock()
_mb_last_request = 0.0


class SpotifyError(Exception):
    pass


def configured() -> bool:
    return bool(settings.spotify_client_id and settings.spotify_client_secret and settings.spotify_redirect_uri)


def _state_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.secret_key, salt="resonar-spotify-oauth")


def authorization_url(user: User) -> str:
    if not configured():
        raise SpotifyError("Spotify no está configurado en el servidor")
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")
    state = _state_serializer().dumps({"user_id": user.id, "verifier": verifier})
    query = urlencode(
        {
            "client_id": settings.spotify_client_id,
            "response_type": "code",
            "redirect_uri": settings.spotify_redirect_uri,
            "scope": _SCOPES,
            "state": state,
            "code_challenge_method": "S256",
            "code_challenge": challenge,
        }
    )
    return f"{_AUTHORIZE_URL}?{query}"


def verify_state(state: str, user: User) -> str:
    try:
        payload = _state_serializer().loads(state, max_age=_STATE_MAX_AGE_SECONDS)
    except BadData as exc:
        raise SpotifyError("La conexión con Spotify ha caducado. Inténtalo de nuevo.") from exc
    if not isinstance(payload, dict) or payload.get("user_id") != user.id or not isinstance(payload.get("verifier"), str):
        raise SpotifyError("La conexión con Spotify no coincide con tu sesión")
    return payload["verifier"]


async def _token_request(data: dict[str, str]) -> dict[str, Any]:
    auth = (settings.spotify_client_id, settings.spotify_client_secret)
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(_TOKEN_URL, data=data, auth=auth)
    if response.status_code >= 400:
        logger.warning("Spotify token exchange failed: status=%s body=%s", response.status_code, response.text[:400])
        raise SpotifyError("Spotify rechazó la autorización")
    payload = response.json()
    if not isinstance(payload, dict) or not payload.get("access_token"):
        raise SpotifyError("Spotify no devolvió un token de acceso")
    return payload


async def complete_connection(db: DbSession, user: User, *, code: str, state: str) -> SpotifyConnection:
    verifier = verify_state(state, user)
    token = await _token_request(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.spotify_redirect_uri,
            "code_verifier": verifier,
        }
    )
    async with httpx.AsyncClient(timeout=20.0) as client:
        profile = await client.get(f"{_API_URL}/me", headers={"Authorization": f"Bearer {token['access_token']}"})
    if profile.status_code >= 400:
        raise SpotifyError("No se pudo leer el perfil de Spotify")
    profile_data = profile.json()
    spotify_user_id = str(profile_data.get("id") or "")
    if not spotify_user_id:
        raise SpotifyError("Spotify no devolvió el identificador de usuario")
    expires_at = utcnow() + timedelta(seconds=max(0, int(token.get("expires_in") or 0)))
    connection = db.scalar(select(SpotifyConnection).where(SpotifyConnection.user_id == user.id))
    if connection is None:
        connection = SpotifyConnection(user_id=user.id, spotify_user_id=spotify_user_id, access_token_encrypted="")
        db.add(connection)
    connection.spotify_user_id = spotify_user_id
    connection.access_token_encrypted = encrypt_secret(str(token["access_token"]), settings.secret_key)
    refresh_token = token.get("refresh_token")
    if isinstance(refresh_token, str) and refresh_token:
        connection.refresh_token_encrypted = encrypt_secret(refresh_token, settings.secret_key)
    connection.expires_at = expires_at
    db.commit()
    db.refresh(connection)
    return connection


async def _access_token(db: DbSession, user: User) -> str:
    connection = db.scalar(select(SpotifyConnection).where(SpotifyConnection.user_id == user.id))
    if connection is None:
        raise SpotifyError("Conecta Spotify primero")
    token = decrypt_secret(connection.access_token_encrypted, settings.secret_key)
    if not token:
        raise SpotifyError("La conexión de Spotify ya no es válida")
    expires_at = connection.expires_at
    # SQLite commonly round-trips DateTime values without tzinfo even when the
    # column declares timezone=True. Treat those persisted values as UTC.
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at is None or expires_at > utcnow() + timedelta(seconds=45):
        return token
    refresh = decrypt_secret(connection.refresh_token_encrypted or "", settings.secret_key)
    if not refresh:
        raise SpotifyError("Vuelve a conectar Spotify para renovar el acceso")
    payload = await _token_request({"grant_type": "refresh_token", "refresh_token": refresh})
    connection.access_token_encrypted = encrypt_secret(str(payload["access_token"]), settings.secret_key)
    if isinstance(payload.get("refresh_token"), str) and payload["refresh_token"]:
        connection.refresh_token_encrypted = encrypt_secret(payload["refresh_token"], settings.secret_key)
    connection.expires_at = utcnow() + timedelta(seconds=max(0, int(payload.get("expires_in") or 0)))
    db.commit()
    return str(payload["access_token"])


async def _spotify_get(db: DbSession, user: User, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    token = await _access_token(db, user)
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{_API_URL}{path}", params=params, headers={"Authorization": f"Bearer {token}"})
    if response.status_code == 401:
        # A revoked/expired token must not be treated as an empty playlist list.
        raise SpotifyError("La autorización de Spotify ha caducado. Vuelve a conectar Spotify.")
    if response.status_code >= 400:
        logger.warning("Spotify API request failed: path=%s status=%s body=%s", path, response.status_code, response.text[:400])
        raise SpotifyError("Spotify no pudo devolver tus playlists")
    data = response.json()
    return data if isinstance(data, dict) else {}


async def list_playlists(db: DbSession, user: User) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    offset = 0
    while True:
        payload = await _spotify_get(db, user, "/me/playlists", {"limit": 50, "offset": offset})
        items = payload.get("items", [])
        if not isinstance(items, list):
            break
        for item in items:
            if not isinstance(item, dict) or not item.get("id") or not item.get("name"):
                continue
            images = item.get("images") if isinstance(item.get("images"), list) else []
            image = next((entry.get("url") for entry in images if isinstance(entry, dict) and entry.get("url")), None)
            owner = item.get("owner") if isinstance(item.get("owner"), dict) else {}
            tracks = item.get("tracks") if isinstance(item.get("tracks"), dict) else {}
            result.append({"id": str(item["id"]), "name": str(item["name"]), "description": item.get("description"), "image": image, "track_count": int(tracks.get("total") or 0), "owner_name": owner.get("display_name")})
        if not payload.get("next"):
            break
        offset += len(items)
    return result


def _find_local_track(db: DbSession, title: str, artist: str) -> Track | None:
    return db.scalar(
        select(Track)
        .where(
            Track.available.is_(True),
            func.lower(Track.title) == title.casefold(),
            func.lower(Track.artist) == artist.casefold(),
        )
        .order_by(Track.updated_at.desc())
    )


async def _playlist_items(db: DbSession, user: User, spotify_playlist_id: str) -> list[dict[str, Any]]:
    tracks: list[dict[str, Any]] = []
    offset = 0
    while True:
        payload = await _spotify_get(db, user, f"/playlists/{spotify_playlist_id}/items", {"limit": 100, "offset": offset})
        items = payload.get("items", [])
        if not isinstance(items, list):
            break
        for item in items:
            source = item.get("item") or item.get("track") if isinstance(item, dict) else None
            if not isinstance(source, dict) or source.get("type") != "track" or not source.get("id") or not source.get("name"):
                continue
            artists = source.get("artists") if isinstance(source.get("artists"), list) else []
            artist = ", ".join(str(entry.get("name")) for entry in artists if isinstance(entry, dict) and entry.get("name"))
            if not artist:
                continue
            album = source.get("album") if isinstance(source.get("album"), dict) else {}
            external_ids = source.get("external_ids") if isinstance(source.get("external_ids"), dict) else {}
            tracks.append({
                "spotify_id": str(source["id"]), "title": str(source["name"]), "artist": artist,
                "album": album.get("name"), "year": str(album.get("release_date") or "")[:4],
                "duration": round(int(source.get("duration_ms") or 0) / 1000) or None,
                "isrc": external_ids.get("isrc"),
            })
        if not payload.get("next"):
            break
        offset += len(items)
    return tracks


async def import_playlists(db: DbSession, user: User, playlist_ids: list[str]) -> tuple[list[Playlist], int, int]:
    available = {item["id"]: item for item in await list_playlists(db, user)}
    selected = [available[playlist_id] for playlist_id in playlist_ids if playlist_id in available]
    if not selected:
        raise SpotifyError("No se encontró ninguna playlist seleccionada en tu cuenta de Spotify")
    imported: list[Playlist] = []
    imported_tracks = 0
    matched_tracks = 0
    for source in selected:
        playlist = playlist_service.create_playlist(db, user=user, name=source["name"], description="Importada desde Spotify")
        imported.append(playlist)
        for item in await _playlist_items(db, user, source["id"]):
            track = _find_local_track(db, item["title"], item["artist"])
            if track is not None:
                matched_tracks += 1
            else:
                try:
                    year = int(item["year"]) if item["year"].isdigit() else None
                except (TypeError, ValueError):
                    year = None
                track = library_service.upsert_external_track(
                    db,
                    ExternalTrack(
                        provider="spotify",
                        provider_id=item["spotify_id"],
                        title=item["title"], artist=item["artist"], album=item["album"], year=year,
                        duration=item["duration"], available=False, status="REQUESTABLE",
                        metadata={"isrc": item["isrc"]} if item["isrc"] else None,
                    ),
                )
            playlist_service.add_track(db, playlist, track)
            imported_tracks += 1
    return imported, imported_tracks, matched_tracks


async def resolve_musicbrainz_recording(track: Track) -> str | None:
    """Resolve a deferred Spotify entry only when it is actually requested."""
    metadata: dict[str, Any] = {}
    try:
        import json
        metadata = json.loads(track.metadata_json or "{}")
    except (TypeError, ValueError):
        pass
    query = f"isrc:{metadata['isrc']}" if metadata.get("isrc") else f'recording:"{track.title}" AND artist:"{track.artist}"'
    global _mb_last_request
    async with _mb_lock:
        delay = 1.1 - (asyncio.get_running_loop().time() - _mb_last_request)
        if delay > 0:
            await asyncio.sleep(delay)
        _mb_last_request = asyncio.get_running_loop().time()
        async with httpx.AsyncClient(timeout=settings.musicbrainz_timeout_seconds) as client:
            response = await client.get(_MUSICBRAINZ_URL, params={"query": query, "fmt": "json", "limit": 1}, headers={"User-Agent": _MUSICBRAINZ_USER_AGENT})
    if response.status_code >= 400:
        logger.warning("MusicBrainz Spotify resolution failed: status=%s", response.status_code)
        return None
    recordings = response.json().get("recordings", [])
    if not isinstance(recordings, list) or not recordings or not isinstance(recordings[0], dict):
        return None
    value = recordings[0].get("id")
    return str(value) if value else None
