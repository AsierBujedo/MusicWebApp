"""Development/test mock implementations of the external services.

Enabled with ``MOCK_EXTERNAL_SERVICES=true`` so the whole backend runs and is
testable without DroppedNeedle, Navidrome or slskd present. The catalog mirrors
the frontend's seed data so the app feels populated in local development.
"""
from __future__ import annotations

import asyncio
from typing import AsyncIterator, List, Optional
from urllib.parse import quote

from app.services.integrations.base import (
    ExternalAlbum,
    ExternalArtist,
    ExternalSearch,
    ExternalTrack,
    HealthResult,
    StreamHandle,
)


def _cover(seed: str) -> str:
    # Matches the frontend's deterministic cover endpoint.
    return f"/api/cover?seed={quote(seed)}"


# (provider_id, title, artist, album, year, duration, available)
_CATALOG: List[ExternalTrack] = [
    ExternalTrack("navidrome", "nd-1", "One More Time", "Daft Punk", "Discovery", "al1", "ar1", 2001, 320, _cover("Daft Punk-Discovery"), True),
    ExternalTrack("navidrome", "nd-2", "Harder, Better, Faster, Stronger", "Daft Punk", "Discovery", "al1", "ar1", 2001, 224, _cover("Daft Punk-Discovery"), True),
    ExternalTrack("droppedneedle", "dn-3", "Around the World", "Daft Punk", "Homework", "al2", "ar1", 1997, 429, _cover("Daft Punk-Homework"), False),
    ExternalTrack("navidrome", "nd-5", "Instant Crush", "Daft Punk", "Random Access Memories", "al3", "ar1", 2013, 337, _cover("Daft Punk-Random Access Memories"), True),
    ExternalTrack("navidrome", "nd-6", "Houdini", "Dua Lipa", "Radical Optimism", "al4", "ar2", 2024, 186, _cover("Dua Lipa-Radical Optimism"), True),
    ExternalTrack("navidrome", "nd-7", "Levitating", "Dua Lipa", "Future Nostalgia", "al5", "ar2", 2020, 203, _cover("Dua Lipa-Future Nostalgia"), True),
    ExternalTrack("droppedneedle", "dn-8", "Don't Start Now", "Dua Lipa", "Future Nostalgia", "al5", "ar2", 2020, 183, _cover("Dua Lipa-Future Nostalgia"), False),
    ExternalTrack("navidrome", "nd-9", "Redbone", "Childish Gambino", "Awaken, My Love!", "al6", "ar3", 2016, 327, _cover("Childish Gambino-Awaken"), True),
    ExternalTrack("droppedneedle", "dn-10", "This Is America", "Childish Gambino", "Singles", "al7", "ar3", 2018, 225, _cover("Childish Gambino-Singles"), False),
    ExternalTrack("navidrome", "nd-11", "Midnight City", "M83", "Hurry Up, We're Dreaming", "al8", "ar4", 2011, 244, _cover("M83-Hurry Up"), True),
    ExternalTrack("navidrome", "nd-13", "Blinding Lights", "The Weeknd", "After Hours", "al9", "ar5", 2020, 200, _cover("The Weeknd-After Hours"), True),
    ExternalTrack("navidrome", "nd-16", "Nightcall", "Kavinsky", "OutRun", "al11", "ar6", 2013, 258, _cover("Kavinsky-OutRun"), True),
    ExternalTrack("droppedneedle", "dn-17", "Feel It Still", "Portugal. The Man", "Woodstock", "al12", "ar7", 2017, 163, _cover("Portugal-Woodstock"), False),
    ExternalTrack("navidrome", "nd-18", "Electric Feel", "MGMT", "Oracular Spectacular", "al13", "ar8", 2007, 229, _cover("MGMT-Oracular"), True),
    ExternalTrack("navidrome", "nd-20", "Solar Drift", "Nova Hale", "Aurora Rooms", "al14", "ar9", 2023, 251, _cover("Nova Hale-Aurora Rooms"), True),
]

_ALBUMS: List[ExternalAlbum] = [
    ExternalAlbum("navidrome", "al1", "Discovery", "Daft Punk", "ar1", _cover("Daft Punk-Discovery"), 2001, 14, True),
    ExternalAlbum("droppedneedle", "al2", "Homework", "Daft Punk", "ar1", _cover("Daft Punk-Homework"), 1997, 16, False),
    ExternalAlbum("navidrome", "al5", "Future Nostalgia", "Dua Lipa", "ar2", _cover("Dua Lipa-Future Nostalgia"), 2020, 11, True),
    ExternalAlbum("navidrome", "al9", "After Hours", "The Weeknd", "ar5", _cover("The Weeknd-After Hours"), 2020, 14, True),
]

_ARTISTS: List[ExternalArtist] = [
    ExternalArtist("navidrome", "ar1", "Daft Punk", _cover("artist-Daft Punk"), 4),
    ExternalArtist("navidrome", "ar2", "Dua Lipa", _cover("artist-Dua Lipa"), 3),
    ExternalArtist("navidrome", "ar5", "The Weeknd", _cover("artist-The Weeknd"), 5),
]


def _match(q: str, *fields: Optional[str]) -> bool:
    ql = q.lower()
    return any(ql in (f or "").lower() for f in fields)


class MockNavidromeClient:
    async def health(self) -> HealthResult:
        return "online", "Biblioteca sincronizada (mock)"

    async def search(self, query: str, limit: int) -> ExternalSearch:
        tracks = [t for t in _CATALOG if t.available and _match(query, t.title, t.artist, t.album)][:limit]
        albums = [a for a in _ALBUMS if a.available and _match(query, a.title, a.artist)][:limit]
        artists = [a for a in _ARTISTS if _match(query, a.name)][:limit]
        return ExternalSearch(tracks=tracks, albums=albums, artists=artists)

    async def get_track(self, provider_id: str) -> Optional[ExternalTrack]:
        return next((t for t in _CATALOG if t.provider_id == provider_id and t.available), None)

    async def open_stream(self, provider_id: str, range_header: Optional[str]) -> StreamHandle:
        # Emit a short run of silence so the <audio> element has something to play.
        total = 64 * 1024
        start, end = 0, total - 1
        status_code = 200
        if range_header and range_header.startswith("bytes="):
            rng = range_header.removeprefix("bytes=").split("-")
            try:
                start = int(rng[0]) if rng[0] else 0
                if len(rng) > 1 and rng[1]:
                    end = int(rng[1])
            except ValueError:
                start, end = 0, total - 1
            status_code = 206
        length = max(0, end - start + 1)

        async def gen() -> AsyncIterator[bytes]:
            remaining = length
            chunk = 8 * 1024
            while remaining > 0:
                n = min(chunk, remaining)
                yield b"\x00" * n
                remaining -= n
                await asyncio.sleep(0)

        headers = {
            "Content-Type": "audio/mpeg",
            "Accept-Ranges": "bytes",
            "Content-Length": str(length),
        }
        if status_code == 206:
            headers["Content-Range"] = f"bytes {start}-{end}/{total}"
        return StreamHandle(status_code=status_code, headers=headers, body=gen())

    async def open_cover(self, provider_id: str) -> StreamHandle:
        async def gen() -> AsyncIterator[bytes]:
            yield b""

        return StreamHandle(status_code=404, headers={}, body=gen())

    async def aclose(self) -> None:
        return None


class MockDroppedNeedleClient:
    async def health(self) -> HealthResult:
        return "online", "Cola vacía (mock)"

    async def search(self, query: str, limit: int) -> List[ExternalTrack]:
        return [t for t in _CATALOG if _match(query, t.title, t.artist, t.album)][:limit]

    async def request(self, *, type: str, title: str, artist: str, provider_id: Optional[str]) -> dict:
        return {"accepted": True, "external_id": f"dn-req-{provider_id or title}"}

    async def get_status(self, external_id: str) -> dict:
        # The worker drives the simulated lifecycle; nothing external to report.
        return {"external_id": external_id, "state": "unknown"}

    async def aclose(self) -> None:
        return None


class MockSlskdClient:
    async def health(self) -> HealthResult:
        return "online", "Conectado (mock)"

    async def get_download_status(self, external_id: str) -> dict:
        return {"external_id": external_id, "state": "unknown", "progress": None}

    async def aclose(self) -> None:
        return None
