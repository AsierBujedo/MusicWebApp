"""Adapter interfaces and DTOs for external services.

Business services depend on these Protocols, never on concrete HTTP code, so
integrations are trivially mockable in tests and swappable in production.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, AsyncIterator, List, Optional, Protocol, Tuple


# --- Data transfer objects (provider-neutral) ---

@dataclass
class ExternalTrack:
    provider: str
    provider_id: str
    title: str
    artist: str
    album: Optional[str] = None
    album_id: Optional[str] = None
    artist_id: Optional[str] = None
    year: Optional[int] = None
    duration: Optional[int] = None
    cover: Optional[str] = None
    # Provider-private cover-art identifier. It is resolved by the backend
    # proxy and must never be sent to the browser as an upstream URL.
    cover_id: Optional[str] = None
    # True when the track is present and playable in the library right now.
    available: bool = False
    # Optional provider state (for example a DroppedNeedle request already in
    # progress). When omitted, availability determines the public state.
    status: Optional[str] = None
    # Provider metadata retained server-side (for example a MusicBrainz release
    # ID used by the authenticated cover-art proxy).
    metadata: Optional[dict[str, Any]] = None


@dataclass
class ExternalAlbum:
    provider: str
    provider_id: str
    title: str
    artist: str
    artist_id: Optional[str] = None
    cover: Optional[str] = None
    year: Optional[int] = None
    track_count: Optional[int] = None
    available: bool = False


@dataclass
class ExternalArtist:
    provider: str
    provider_id: str
    name: str
    image: Optional[str] = None
    album_count: Optional[int] = None


@dataclass
class ExternalSearch:
    tracks: List[ExternalTrack] = field(default_factory=list)
    albums: List[ExternalAlbum] = field(default_factory=list)
    artists: List[ExternalArtist] = field(default_factory=list)


@dataclass
class StreamHandle:
    """A streamable audio response. ``body`` is an async byte iterator so the
    file is never fully loaded into memory."""

    status_code: int
    headers: dict
    body: AsyncIterator[bytes]


# status is one of: "online" | "degraded" | "offline"
HealthResult = Tuple[str, Optional[str]]


# --- Protocols ---

class NavidromeClient(Protocol):
    async def health(self) -> HealthResult: ...
    async def search(self, query: str, limit: int) -> ExternalSearch: ...
    async def get_track(self, provider_id: str) -> Optional[ExternalTrack]: ...
    async def open_stream(self, provider_id: str, range_header: Optional[str]) -> StreamHandle: ...
    async def open_cover(self, provider_id: str) -> StreamHandle: ...
    async def aclose(self) -> None: ...


class DroppedNeedleClient(Protocol):
    async def health(self) -> HealthResult: ...
    async def search(self, query: str, limit: int) -> List[ExternalTrack]: ...
    async def request(self, *, type: str, title: str, artist: str, provider_id: Optional[str]) -> dict: ...
    async def get_status(self, external_id: str) -> dict: ...
    async def get_artist_catalog(self, artist_id: str, name: Optional[str] = None) -> dict: ...
    async def get_album_catalog(self, album_id: str, artist: Optional[str] = None, title: Optional[str] = None) -> dict: ...
    async def request_album(self, *, musicbrainz_id: str, artist: str, album: str, year: Optional[int], artist_mbid: Optional[str]) -> dict: ...
    async def request_albums(self, items: List[dict]) -> dict: ...
    async def aclose(self) -> None: ...


class SlskdClient(Protocol):
    async def health(self) -> HealthResult: ...
    async def get_download_status(self, external_id: str) -> dict: ...
    async def aclose(self) -> None: ...
