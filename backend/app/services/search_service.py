"""Search aggregation across providers.

Merges results from Navidrome (owned library) and DroppedNeedle (acquirable
catalog), upserts every track behind a stable backend id, and returns the exact
``SearchResults`` shape the frontend expects. Albums and artists are surfaced
directly from the providers using their native ids so a track's ``albumId`` /
``artistId`` cross-references stay valid.
"""
from __future__ import annotations

import unicodedata
from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.config import settings
from app.services import library_service
from app.services.integrations import get_droppedneedle_client, get_navidrome_client
from app.services.integrations.base import ExternalAlbum, ExternalArtist, ExternalTrack
from app.services.serializers import track_out
from app.models.track import Track


def _album_out(a: ExternalAlbum) -> Dict[str, Any]:
    return {
        "id": a.provider_id,
        "title": a.title,
        "artist": a.artist,
        "artistId": a.artist_id,
        "cover": a.cover or (f"/api/covers/release-group/{a.provider_id}" if a.provider == "droppedneedle" else None),
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


def _normalise_query(query: str) -> str:
    q = query.strip()[: settings.search_max_query_length]
    return q if len(q) >= settings.search_min_query_length else ""


def _fold(value: str | None) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    return "".join(char for char in value if not unicodedata.combining(char)).casefold()


def _relevance(query: str, *, artist: str = "", title: str = "", album: str = "") -> int:
    """Return a conservative relevance score; zero means unrelated."""
    needle = _fold(query)
    tokens = [token for token in needle.split() if token]
    artist_text, title_text, album_text = _fold(artist), _fold(title), _fold(album)
    combined = f"{artist_text} {title_text} {album_text}"
    if not needle or not tokens or not all(token in combined for token in tokens):
        return 0
    if needle in artist_text:
        return 100
    if all(token in artist_text for token in tokens):
        return 90
    if needle in title_text:
        return 80
    if needle in album_text:
        return 70
    return 60


def _relevant_tracks(items: List[ExternalTrack], query: str) -> List[ExternalTrack]:
    ranked = [(item, _relevance(query, artist=item.artist, title=item.title, album=item.album or "")) for item in items]
    return [item for item, score in sorted(ranked, key=lambda entry: (-entry[1], not entry[0].available, entry[0].title.casefold())) if score]


def _relevant_albums(items: List[ExternalAlbum], query: str) -> List[ExternalAlbum]:
    return [item for item in items if _relevance(query, artist=item.artist, title=item.title)]


def _relevant_artists(items: List[ExternalArtist], query: str) -> List[ExternalArtist]:
    return [item for item in items if _relevance(query, artist=item.name)]


def _cached_tracks(db: DbSession, query: str, limit: int) -> List[Track]:
    """Return catalogue rows Resonar has already learned about.

    Current DroppedNeedle releases deliberately expose artists and albums from
    ``/search`` but not recordings.  Album pages still cache their recordings
    in Resonar, though, and those must remain searchable even while
    MusicBrainz is slow or temporarily unavailable.  Keep this a bounded
    in-process filter so it works on both SQLite and PostgreSQL and shares the
    same conservative relevance rules as provider results.
    """
    candidates = db.scalars(
        select(Track)
        .order_by(Track.available.desc(), Track.updated_at.desc())
        .limit(max(limit * 20, 200))
    ).all()
    ranked = [
        (
            item,
            _relevance(query, artist=item.artist, title=item.title, album=item.album or ""),
        )
        for item in candidates
    ]
    return [
        item
        for item, score in sorted(
            ranked,
            key=lambda entry: (-entry[1], not entry[0].available, entry[0].title.casefold()),
        )
        if score
    ][:limit]


async def search_local(db: DbSession, query: str) -> Dict[str, Any]:
    """Fast path: search only the already playable Navidrome library."""
    q = _normalise_query(query)
    if not q:
        return {"tracks": [], "albums": [], "artists": []}
    client = get_navidrome_client()
    try:
        result = await client.search(q, settings.search_result_limit)
    finally:
        await client.aclose()
    tracks = _relevant_tracks(result.tracks, q)
    return {
        "tracks": [track_out(library_service.upsert_external_track(db, item)) for item in tracks],
        "albums": [_album_out(item) for item in _relevant_albums(result.albums, q)],
        "artists": [_artist_out(item) for item in _relevant_artists(result.artists, q)],
    }


async def search_external(db: DbSession, query: str) -> Dict[str, Any]:
    """Slow path: search the acquirable catalogue without waiting on local IO."""
    q = _normalise_query(query)
    if not q:
        return {"tracks": [], "albums": [], "artists": []}
    client = get_droppedneedle_client()
    try:
        tracks = _relevant_tracks(await client.search(q, settings.search_result_limit), q)
    finally:
        await client.aclose()

    # Preserve previously opened album tracks when the live recording lookup
    # is unavailable.  This is intentionally merged with (rather than used
    # instead of) MusicBrainz so fresh searches still discover new music.
    cached = _cached_tracks(db, q, settings.search_result_limit)
    live_keys = {(item.title.casefold(), item.artist.casefold()) for item in tracks}
    cached_out = [
        track_out(item)
        for item in cached
        if (item.title.casefold(), item.artist.casefold()) not in live_keys
    ]
    tracks_out = [track_out(library_service.upsert_external_track(db, item)) for item in tracks]
    tracks_out.extend(cached_out)
    artists: list[ExternalArtist] = []
    albums: list[ExternalAlbum] = []
    artist_index: dict[str, ExternalArtist] = {}
    album_keys: dict[str, set[str]] = {}
    seen_albums: set[tuple[str, str]] = set()
    for item in tracks:
        artist_key = item.artist.casefold()
        if item.artist and artist_key not in artist_index:
            artist = ExternalArtist(
                provider=item.provider,
                provider_id=item.artist_id or item.artist,
                name=item.artist,
                image=item.cover or (f"/api/covers/release-group/{item.album_id}" if item.album_id else None),
            )
            artists.append(artist)
            artist_index[artist_key] = artist
        if item.album:
            key = (item.album.casefold(), artist_key)
            if key not in seen_albums:
                albums.append(ExternalAlbum(provider=item.provider, provider_id=item.album_id or item.album, title=item.album, artist=item.artist, artist_id=item.artist_id, cover=item.cover, year=item.year, available=item.available))
                seen_albums.add(key)
            album_keys.setdefault(artist_key, set()).add(str(item.album_id or item.album.casefold()))
    for key, artist in artist_index.items():
        artist.album_count = len(album_keys.get(key, set()))
    return {"tracks": tracks_out, "albums": [_album_out(item) for item in albums], "artists": [_artist_out(item) for item in artists]}


async def search(db: DbSession, query: str) -> Dict[str, Any]:
    q = query.strip()
    limit = settings.search_result_limit
    if len(q) < settings.search_min_query_length:
        return {"tracks": [], "albums": [], "artists": []}
    q = q[: settings.search_max_query_length]

    navidrome = get_navidrome_client()
    droppedneedle = get_droppedneedle_client()

    try:
        nav = await navidrome.search(q, limit)
        dn_tracks: List[ExternalTrack] = await droppedneedle.search(q, limit)
    finally:
        await navidrome.aclose()
        await droppedneedle.aclose()

    nav.tracks = _relevant_tracks(nav.tracks, q)
    nav.albums = _relevant_albums(nav.albums, q)
    nav.artists = _relevant_artists(nav.artists, q)
    dn_tracks = _relevant_tracks(dn_tracks, q)

    # Merge tracks: owned library first, then acquirable ones not already owned.
    # Prefer Navidrome for matching songs: it is the only playback provider.
    # This avoids exposing a DroppedNeedle catalogue ID as a streamable track.
    def identity(track: ExternalTrack) -> tuple[str, str]:
        return track.title.casefold().strip(), track.artist.casefold().strip()

    seen = {identity(t) for t in nav.tracks}
    merged: List[ExternalTrack] = list(nav.tracks)
    for t in dn_tracks:
        key = identity(t)
        if key not in seen:
            merged.append(t)
            seen.add(key)

    tracks_out: List[Dict[str, Any]] = []
    for ext in merged:
        track = library_service.upsert_external_track(db, ext)
        tracks_out.append(track_out(track))
    # Keep the legacy aggregate endpoint behaviour aligned with the split
    # frontend endpoints: cached catalogue tracks remain useful during an
    # upstream MusicBrainz outage.
    for cached in _cached_tracks(db, q, limit):
        key = identity(cached)
        if key not in seen:
            tracks_out.append(track_out(cached))
            seen.add(key)

    # DroppedNeedle's public search is primarily track-oriented. Derive artist
    # and release cards from those tracks too, so an artist absent from the
    # local Navidrome library (for example Amaral) still opens its catalogue.
    artists = list(nav.artists)
    seen_artists = {a.name.casefold() for a in artists}
    albums = list(nav.albums)
    seen_albums = {(a.title.casefold(), a.artist.casefold()) for a in albums}
    # MusicBrainz recording searches and DroppedNeedle's track facet do not
    # include an artist album total. Count the distinct releases represented
    # in this response so the UI never misleadingly prints “0 álbumes”.
    albums_per_artist: dict[str, set[str]] = {}
    for ext in merged:
        artist_key = ext.artist.casefold()
        if ext.album:
            albums_per_artist.setdefault(artist_key, set()).add(
                str(ext.album_id or ext.album.casefold())
            )
        if ext.artist and ext.artist.casefold() not in seen_artists:
            artists.append(ExternalArtist(provider=ext.provider, provider_id=ext.artist_id or ext.artist, name=ext.artist, image=ext.cover or (f"/api/covers/release-group/{ext.album_id}" if ext.provider == "droppedneedle" and ext.album_id else None)))
            seen_artists.add(ext.artist.casefold())
        if ext.album and (ext.album.casefold(), ext.artist.casefold()) not in seen_albums:
            albums.append(ExternalAlbum(provider=ext.provider, provider_id=ext.album_id or ext.album, title=ext.album, artist=ext.artist, artist_id=ext.artist_id, cover=ext.cover, year=ext.year, available=ext.available))
            seen_albums.add((ext.album.casefold(), ext.artist.casefold()))

    for artist in artists:
        if artist.album_count is None:
            artist.album_count = len(albums_per_artist.get(artist.name.casefold(), set()))

    return {
        "tracks": tracks_out,
        "albums": [_album_out(a) for a in albums[:limit]],
        "artists": [_artist_out(a) for a in artists[:limit]],
    }
