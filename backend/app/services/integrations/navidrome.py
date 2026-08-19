"""Navidrome integration.

Navidrome implements the well-documented Subsonic API, which we use here for
search, metadata and streaming. Authentication uses the Subsonic token scheme
(``token = md5(password + salt)``) so the raw password is never sent on the
wire and, critically, never reaches the browser.

The factory ``get_navidrome_client`` returns the mock implementation when
``MOCK_EXTERNAL_SERVICES`` is enabled.
"""
from __future__ import annotations

import hashlib
import logging
import secrets
from typing import AsyncIterator, Optional

import httpx

from app.config import settings
from app.services.integrations.base import (
    ExternalAlbum,
    ExternalArtist,
    ExternalSearch,
    ExternalTrack,
    HealthResult,
    StreamHandle,
)
from app.services.integrations.mocks import MockNavidromeClient

logger = logging.getLogger(__name__)

_SUBSONIC_CLIENT = "homemusic"
_SUBSONIC_VERSION = "1.16.1"


class RealNavidromeClient:
    def __init__(self) -> None:
        self._base = settings.navidrome_url.rstrip("/")
        self._username = settings.navidrome_username
        self._password = settings.navidrome_password
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(10.0, read=None))

    def _auth_params(self) -> dict:
        salt = secrets.token_hex(8)
        token = hashlib.md5(f"{self._password}{salt}".encode("utf-8")).hexdigest()
        return {
            "u": self._username,
            "t": token,
            "s": salt,
            "v": _SUBSONIC_VERSION,
            "c": _SUBSONIC_CLIENT,
            "f": "json",
        }

    def _url(self, view: str) -> str:
        return f"{self._base}/rest/{view}"

    async def health(self) -> HealthResult:
        if not self._base:
            return "offline", "Sin configurar"
        try:
            resp = await self._client.get(self._url("ping.view"), params=self._auth_params())
            data = resp.json().get("subsonic-response", {})
            if data.get("status") == "ok":
                return "online", "Conectado"
            return "degraded", "Respuesta inesperada"
        except Exception:
            logger.warning("Navidrome health check failed", exc_info=True)
            return "offline", "No responde"

    async def search(self, query: str, limit: int) -> ExternalSearch:
        params = self._auth_params()
        params.update({"query": query, "songCount": limit, "albumCount": limit, "artistCount": limit})
        try:
            resp = await self._client.get(self._url("search3.view"), params=params)
            body = resp.json().get("subsonic-response", {}).get("searchResult3", {})
        except Exception:
            logger.warning("Navidrome search failed", exc_info=True)
            return ExternalSearch()

        tracks = [self._song_to_track(s) for s in body.get("song", [])]
        albums = [
            ExternalAlbum(
                provider="navidrome",
                provider_id=str(a.get("id")),
                title=a.get("name", ""),
                artist=a.get("artist", ""),
                artist_id=str(a.get("artistId")) if a.get("artistId") else None,
                year=a.get("year"),
                track_count=a.get("songCount"),
                available=True,
            )
            for a in body.get("album", [])
        ]
        artists = [
            ExternalArtist(
                provider="navidrome",
                provider_id=str(a.get("id")),
                name=a.get("name", ""),
                album_count=a.get("albumCount"),
            )
            for a in body.get("artist", [])
        ]
        return ExternalSearch(tracks=tracks, albums=albums, artists=artists)

    async def get_track(self, provider_id: str) -> Optional[ExternalTrack]:
        params = self._auth_params()
        params["id"] = provider_id
        try:
            resp = await self._client.get(self._url("getSong.view"), params=params)
            song = resp.json().get("subsonic-response", {}).get("song")
        except Exception:
            logger.warning("Navidrome getSong failed", exc_info=True)
            return None
        if not song:
            return None
        return self._song_to_track(song)

    async def open_stream(self, provider_id: str, range_header: Optional[str]) -> StreamHandle:
        params = self._auth_params()
        params["id"] = provider_id
        headers = {}
        if range_header:
            headers["Range"] = range_header

        req = self._client.build_request("GET", self._url("stream.view"), params=params, headers=headers)
        resp = await self._client.send(req, stream=True)

        async def body() -> AsyncIterator[bytes]:
            try:
                async for chunk in resp.aiter_bytes():
                    yield chunk
            finally:
                await resp.aclose()

        forwarded = {}
        for h in ("content-type", "content-length", "content-range", "accept-ranges"):
            if h in resp.headers:
                forwarded[h.title()] = resp.headers[h]
        forwarded.setdefault("Accept-Ranges", "bytes")
        return StreamHandle(status_code=resp.status_code, headers=forwarded, body=body())

    async def open_cover(self, provider_id: str) -> StreamHandle:
        params = self._auth_params()
        params["id"] = provider_id
        req = self._client.build_request("GET", self._url("getCoverArt.view"), params=params)
        resp = await self._client.send(req, stream=True)

        async def body() -> AsyncIterator[bytes]:
            try:
                async for chunk in resp.aiter_bytes():
                    yield chunk
            finally:
                await resp.aclose()

        headers = {}
        for header in ("content-type", "content-length", "cache-control"):
            if header in resp.headers:
                headers[header.title()] = resp.headers[header]
        return StreamHandle(status_code=resp.status_code, headers=headers, body=body())

    def _song_to_track(self, s: dict) -> ExternalTrack:
        return ExternalTrack(
            provider="navidrome",
            provider_id=str(s.get("id")),
            title=s.get("title", ""),
            artist=s.get("artist", ""),
            artist_id=str(s.get("artistId")) if s.get("artistId") else None,
            album=s.get("album"),
            album_id=str(s.get("albumId")) if s.get("albumId") else None,
            year=s.get("year"),
            duration=s.get("duration"),
            cover_id=str(s.get("coverArt")) if s.get("coverArt") else None,
            available=True,
        )

    async def aclose(self) -> None:
        await self._client.aclose()


def get_navidrome_client():
    if settings.mock_external_services:
        return MockNavidromeClient()
    return RealNavidromeClient()
