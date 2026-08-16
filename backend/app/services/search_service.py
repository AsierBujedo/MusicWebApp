"""Search aggregation across providers.

Merges results from Navidrome (owned library) and DroppedNeedle (acquirable
catalog), upserts every track behind a stable backend id, and returns the exact
``SearchResults`` shape the frontend expects. Albums and artists are surfaced
directly from the providers using their native ids so a track's ``albumId`` /
``artistId`` cross-references stay valid.
"""
from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy.orm import Session as DbSession

from app.config import settings
from app.services import library_service
from app.services.integrations import get_droppedneedle_client, get_navidrome_client
from app.services.integrations.base import ExternalAlbum, ExternalArtist, ExternalTrack
from app.services.serializers import track_out


def _album_out(a: ExternalAlbum) -> Dict[str, Any]:
    return {
        "id": a.provider_id,
        "title": a.title,
        "artist": a.artist,
        "artistId": a.artist_id,
        "cover": a.cover,
        "year": a.year,
        "trackCount": a.track_count,
        "status": "AVAILABLE" if a.available else "REQUESTABLE",
    }


def _artist_out(a: ExternalArtist) -> Dict[str, Any]:
    return {
        "id": a.provider_id,
        "name": a.name,
        "image": a.image,
        "albumCount": a.album_count,
    }


async def search(db: DbSession, query: str) -> Dict[str, Any]:
    q = query.strip()
    limit = settings.search_result_limit
    if len(q) < settings.search_min_query_length:
        return {"tracks": [], "albums": [], "artists": []}
    q = q[: settings.search_max_query_length]

    navidrome = get_navidrome_client()
    droppedneedle = get_droppedneedle_client()

    nav = await navidrome.search(q, limit)
    dn_tracks: List[ExternalTrack] = await droppedneedle.search(q, limit)

    # Merge tracks: owned library first, then acquirable ones not already owned.
    seen = {(t.provider, t.provider_id) for t in nav.tracks}
    merged: List[ExternalTrack] = list(nav.tracks)
    for t in dn_tracks:
        key = (t.provider, t.provider_id)
        if key not in seen:
            merged.append(t)
            seen.add(key)

    tracks_out: List[Dict[str, Any]] = []
    for ext in merged:
        track = library_service.upsert_external_track(db, ext)
        tracks_out.append(track_out(track))

    return {
        "tracks": tracks_out,
        "albums": [_album_out(a) for a in nav.albums],
        "artists": [_artist_out(a) for a in nav.artists],
    }
