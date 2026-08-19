"""Pure functions that convert ORM rows into the exact camelCase JSON shapes the
frontend contract (`types/api.ts`) expects. Keeping this in one place guarantees
every endpoint emits an identical shape and never leaks internal columns
(``file_reference``, ``provider_id``, ``password_hash``...)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session as DbSession

from app.models.base import iso
from app.models.playlist import Playlist
from app.models.track import Track
from app.models.user import User

REQUESTABLE_STATUSES = {"REQUESTABLE", "UNAVAILABLE"}


def _compact(data: Dict[str, Any]) -> Dict[str, Any]:
    """Drop keys whose value is ``None`` so optional fields are simply absent."""
    return {k: v for k, v in data.items() if v is not None}


def track_out(track: Track) -> Dict[str, Any]:
    # Existing library rows may predate cover persistence. Navidrome remains
    # authoritative, so expose the same authenticated proxy for those rows.
    cover = track.cover or (f"/api/covers/{track.id}" if track.provider == "navidrome" else None)
    return _compact(
        {
            "id": track.id,
            "title": track.title,
            "artist": track.artist,
            "artistId": track.artist_id,
            "album": track.album,
            "albumId": track.album_id,
            "cover": cover,
            "year": track.year,
            "duration": track.duration,
            "status": track.status,
            "requestable": track.status in REQUESTABLE_STATUSES,
            "progress": track.progress if track.status == "DOWNLOADING" else None,
        }
    )


def user_out(user: User) -> Dict[str, Any]:
    return _compact(
        {
            "id": user.id,
            "username": user.username,
            "displayName": user.display_name,
            "email": user.email,
            "avatar": user.avatar,
            "role": user.role,
            "active": user.active,
            "lastSeen": iso(user.last_seen),
        }
    )


def request_out(req, *, requested_by_name: Optional[str] = None) -> Dict[str, Any]:
    return _compact(
        {
            "id": req.id,
            "type": req.type,
            "trackId": req.track_id,
            "title": req.title,
            "artist": req.artist,
            "cover": req.cover,
            "status": req.status,
            "progress": req.progress,
            "errorMessage": req.error_message,
            "createdAt": iso(req.created_at),
            "requestedBy": req.requested_by,
            "requestedByName": requested_by_name,
        }
    )


def playlist_out(db: DbSession, pl: Playlist) -> Dict[str, Any]:
    # ``items`` is ordered by position at the relationship level.
    track_ids: List[str] = [item.track_id for item in pl.items]
    tracks: List[Dict[str, Any]] = []
    for item in pl.items:
        track = item.track or db.get(Track, item.track_id)
        if track is not None:
            tracks.append(track_out(track))
    return _compact(
        {
            "id": pl.id,
            "name": pl.name,
            "description": pl.description,
            "cover": pl.cover,
            "trackIds": track_ids,
            "tracks": tracks,
            "createdAt": iso(pl.created_at),
        }
    )


def history_out(entry) -> Optional[Dict[str, Any]]:
    if entry.track is None:
        return None
    return {"track": track_out(entry.track), "playedAt": iso(entry.played_at)}
