"""DroppedNeedle integration (real /api/v1 API).

DroppedNeedle is the acquisition orchestrator. Its real HTTP surface lives under
``/api/v1`` (confirmed against the deployment's OpenAPI document). This adapter
speaks that API directly — it does NOT invent endpoints.

Authentication
--------------
DroppedNeedle has no static API key. We authenticate with username/password:

    POST /api/v1/auth/login  -> { "token": "...", "user": { ... } }

The bearer token is held in server memory and attached as ``Authorization:
Bearer <token>`` on subsequent calls. On a 401 we transparently re-login once
and retry. The token is never logged and never sent to the browser.

Endpoints used
--------------
- POST /api/v1/auth/login
- GET  /api/v1/search?q=...            (artists / albums with in_library, requested, musicbrainz_id)
- POST /api/v1/requests/new            (place an acquisition request by musicbrainz_id)
- GET  /api/v1/requests/active         (in-flight acquisitions)
- GET  /api/v1/downloads               (download/transfer progress)

The factory returns the mock implementation when ``MOCK_EXTERNAL_SERVICES`` is
enabled.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

import httpx

from app.config import settings
from app.services.integrations.base import (
    ExternalAlbum,
    ExternalArtist,
    ExternalSearch,
    ExternalTrack,
    HealthResult,
)
from app.services.integrations.mocks import MockDroppedNeedleClient

logger = logging.getLogger(__name__)

_API = "/api/v1"


def _availability(in_library: bool, requested: bool) -> bool:
    """DroppedNeedle availability -> our ``available`` flag. Only ``in_library``
    means it is playable right now."""
    return bool(in_library)


class RealDroppedNeedleClient:
    def __init__(self) -> None:
        self._base = settings.droppedneedle_url.rstrip("/")
        self._username = settings.droppedneedle_username
        self._password = settings.droppedneedle_password
        self._token: Optional[str] = None
        self._client = httpx.AsyncClient(base_url=self._base, timeout=20.0)
        self._login_lock = asyncio.Lock()

    # -- auth ---------------------------------------------------------------

    async def _login(self) -> None:
        """Authenticate and cache the bearer token. Serialized so concurrent
        callers don't stampede the login endpoint."""
        async with self._login_lock:
            resp = await self._client.post(
                f"{_API}/auth/login",
                json={"username": self._username, "password": self._password},
            )
            resp.raise_for_status()
            token = resp.json().get("token")
            if not token:
                raise RuntimeError("DroppedNeedle login returned no token")
            self._token = token
            # Never log the token itself.
            logger.info("DroppedNeedle authenticated as %s", self._username)

    def _auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token}"} if self._token else {}

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Perform an authenticated request, logging in on demand and retrying
        once on 401 (expired/invalid token)."""
        if self._token is None:
            await self._login()

        resp = await self._client.request(
            method, path, headers={**self._auth_headers(), **kwargs.pop("headers", {})}, **kwargs
        )
        if resp.status_code == 401:
            logger.info("DroppedNeedle token rejected; re-authenticating")
            self._token = None
            await self._login()
            resp = await self._client.request(
                method, path, headers={**self._auth_headers(), **kwargs.pop("headers", {})}, **kwargs
            )
        return resp

    # -- health -------------------------------------------------------------

    async def health(self) -> HealthResult:
        if not self._base:
            return "offline", "Sin configurar"
        try:
            resp = await self._request("GET", f"{_API}/auth/me")
            if resp.status_code < 400:
                return "online", "Conectado"
            return "degraded", f"HTTP {resp.status_code}"
        except Exception:
            logger.warning("DroppedNeedle health check failed", exc_info=True)
            return "offline", "No responde"

    # -- search -------------------------------------------------------------

    async def search(self, query: str, limit: int) -> ExternalSearch:
        try:
            resp = await self._request(
                "GET",
                f"{_API}/search",
                params={"q": query, "limit_artists": limit, "limit_albums": limit},
            )
            resp.raise_for_status()
            payload = resp.json()
        except Exception:
            logger.warning("DroppedNeedle search failed", exc_info=True)
            return ExternalSearch()

        albums = [self._to_album(a) for a in (payload.get("albums") or [])][:limit]
        artists = [self._to_artist(a) for a in (payload.get("artists") or [])][:limit]
        return ExternalSearch(tracks=[], albums=albums, artists=artists)

    def _to_album(self, a: dict) -> ExternalAlbum:
        in_library = bool(a.get("in_library"))
        return ExternalAlbum(
            provider="droppedneedle",
            provider_id=str(a.get("musicbrainz_id") or a.get("id") or ""),
            title=a.get("title", ""),
            artist=a.get("artist", ""),
            cover=a.get("cover_url") or a.get("album_thumb_url") or a.get("thumb_url"),
            year=a.get("year"),
            available=_availability(in_library, bool(a.get("requested"))),
            musicbrainz_id=a.get("musicbrainz_id"),
            requested=bool(a.get("requested")),
        )

    def _to_artist(self, a: dict) -> ExternalArtist:
        return ExternalArtist(
            provider="droppedneedle",
            provider_id=str(a.get("musicbrainz_id") or a.get("id") or ""),
            name=a.get("title") or a.get("artist") or a.get("name", ""),
            image=a.get("thumb_url") or a.get("fanart_url") or a.get("banner_url"),
            musicbrainz_id=a.get("musicbrainz_id"),
        )

    # -- requests -----------------------------------------------------------

    async def request(
        self, *, type: str, title: str, artist: str, musicbrainz_id: Optional[str]
    ) -> dict:
        """Place an acquisition request. DroppedNeedle keys requests on the
        MusicBrainz id, so it is required for a real submission."""
        if not musicbrainz_id:
            return {"accepted": False, "external_id": None, "error": "missing musicbrainz_id"}
        try:
            resp = await self._request(
                "POST",
                f"{_API}/requests/new",
                json={
                    "musicbrainz_id": musicbrainz_id,
                    "type": type,
                    "title": title,
                    "artist": artist,
                },
            )
            resp.raise_for_status()
            data = resp.json() if resp.content else {}
            return {
                "accepted": True,
                "external_id": str(data.get("id") or data.get("task_id") or musicbrainz_id),
                "raw": data,
            }
        except Exception:
            logger.warning("DroppedNeedle request submission failed", exc_info=True)
            return {"accepted": False, "external_id": None}

    async def sync_status(self) -> dict:
        """Aggregate active requests and downloads into a musicbrainz_id-keyed
        status map the worker uses to advance our own request rows."""
        result: dict = {}
        try:
            active = await self._request("GET", f"{_API}/requests/active")
            if active.status_code < 400:
                for item in _as_list(active.json()):
                    mbid = item.get("musicbrainz_id")
                    if not mbid:
                        continue
                    result[str(mbid)] = {
                        "status": _map_state(item.get("status") or item.get("state")),
                        "progress": item.get("progress"),
                        "error": item.get("error") or item.get("error_message"),
                    }
        except Exception:
            logger.warning("DroppedNeedle active requests failed", exc_info=True)

        try:
            downloads = await self._request("GET", f"{_API}/downloads")
            if downloads.status_code < 400:
                for d in _as_list(downloads.json()):
                    mbid = d.get("musicbrainz_id")
                    if not mbid:
                        continue
                    entry = result.setdefault(str(mbid), {})
                    entry.setdefault("status", "DOWNLOADING")
                    if d.get("progress") is not None:
                        entry["progress"] = d.get("progress")
        except Exception:
            logger.warning("DroppedNeedle downloads failed", exc_info=True)

        return result

    async def aclose(self) -> None:
        await self._client.aclose()


def _as_list(payload) -> list:
    """DroppedNeedle collection endpoints may return a bare list or a wrapped
    object; normalize to a list of dicts."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("items", "results", "requests", "downloads", "data"):
            if isinstance(payload.get(key), list):
                return payload[key]
    return []


def _map_state(state: Optional[str]) -> str:
    """Map DroppedNeedle acquisition states to our RequestStatus contract."""
    if not state:
        return "SEARCHING"
    s = state.lower()
    if s in {"available", "complete", "completed", "done", "imported"}:
        return "AVAILABLE"
    if s in {"downloading", "transferring"}:
        return "DOWNLOADING"
    if s in {"searching", "queued", "pending", "wanted"}:
        return "SEARCHING"
    if s in {"failed", "error"}:
        return "FAILED"
    if s in {"rejected", "cancelled", "canceled"}:
        return "REJECTED"
    return "SEARCHING"


def get_droppedneedle_client():
    if settings.mock_external_services:
        return MockDroppedNeedleClient()
    return RealDroppedNeedleClient()
