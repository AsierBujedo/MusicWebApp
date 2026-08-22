"""DroppedNeedle API v1 integration.

DroppedNeedle owns discovery and acquisition. Its bearer token is held only by
this backend; slskd remains a DroppedNeedle dependency, not a second download
orchestrator for this application.
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any, List, Optional

import httpx

from app.config import settings
from app.services.integrations.base import ExternalTrack, HealthResult
from app.services.integrations.mocks import MockDroppedNeedleClient

logger = logging.getLogger(__name__)
_MUSICBRAINZ_API = "https://musicbrainz.org/ws/2"
_MUSICBRAINZ_USER_AGENT = "Resonar/1.0 (self-hosted music catalogue fallback)"
_MUSICBRAINZ_MIN_INTERVAL_SECONDS = 1.1
_MUSICBRAINZ_CACHE_TTL_SECONDS = 600
_musicbrainz_lock = asyncio.Lock()
_musicbrainz_last_request_at = 0.0
_musicbrainz_cache: dict[str, tuple[float, List[ExternalTrack]]] = {}


class RealDroppedNeedleClient:
    def __init__(self) -> None:
        self._base = settings.droppedneedle_url.rstrip("/")
        self._client = httpx.AsyncClient(base_url=self._base, timeout=15.0)
        self._token: Optional[str] = None

    async def _login(self) -> bool:
        if not self._base or not settings.droppedneedle_username or not settings.droppedneedle_password:
            return False
        try:
            response = await self._client.post(
                "/api/v1/auth/login",
                json={"username": settings.droppedneedle_username, "password": settings.droppedneedle_password},
            )
            response.raise_for_status()
            payload = response.json()
            data = payload.get("data", payload) if isinstance(payload, dict) else {}
            token = data.get("access_token") or data.get("accessToken") or data.get("token")
            if isinstance(token, str) and token:
                self._token = token
                return True
        except (httpx.HTTPError, ValueError):
            logger.warning("DroppedNeedle login failed", exc_info=True)
        return False

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        if not self._token and not await self._login():
            raise httpx.HTTPError("DroppedNeedle is not configured or login failed")
        headers = dict(kwargs.pop("headers", {}))
        headers["Authorization"] = f"Bearer {self._token}"
        response = await self._client.request(method, path, headers=headers, **kwargs)
        if response.status_code != httpx.codes.UNAUTHORIZED:
            response.raise_for_status()
            return response

        self._token = None
        if not await self._login():
            response.raise_for_status()
        headers["Authorization"] = f"Bearer {self._token}"
        response = await self._client.request(method, path, headers=headers, **kwargs)
        response.raise_for_status()
        return response

    @staticmethod
    def _payload(response: httpx.Response) -> dict:
        payload = response.json()
        if not isinstance(payload, dict):
            return {}
        data = payload.get("data", payload)
        return data if isinstance(data, dict) else payload

    async def health(self) -> HealthResult:
        if not self._base:
            return "offline", "Sin configurar"
        if not settings.droppedneedle_username or not settings.droppedneedle_password:
            return "degraded", "Faltan credenciales"
        try:
            await self._request("GET", "/api/v1/auth/me")
            return "online", "Conectado"
        except Exception:
            logger.warning("DroppedNeedle health check failed", exc_info=True)
            return "offline", "No responde o credenciales inválidas"

    async def search(self, query: str, limit: int) -> List[ExternalTrack]:
        try:
            # DroppedNeedle API builds have used both ``q`` and ``query``.
            # Sending both is backwards-compatible and prevents a silent empty
            # catalogue when an installation expects the latter.
            response = await self._request("GET", "/api/v1/search", params={"q": query, "query": query})
            raw_payload = response.json()
        except Exception:
            logger.warning("DroppedNeedle search failed", exc_info=True)
            return await self._search_musicbrainz(query, limit)

        payload = raw_payload.get("data", raw_payload) if isinstance(raw_payload, dict) else raw_payload
        if isinstance(payload, list):
            results = payload
        elif isinstance(payload, dict):
            results = payload.get("results", payload.get("items", payload.get("tracks", payload.get("songs", []))))
        else:
            results = []
        if not isinstance(results, list):
            results = []
        tracks: List[ExternalTrack] = []
        for result in results[:limit]:
            if not isinstance(result, dict):
                continue
            # Some API versions wrap the recording object, while others put
            # every field directly in the result.
            item = result.get("recording", result.get("track", result))
            if not isinstance(item, dict):
                continue
            kind = str(result.get("type") or item.get("type") or "track").lower()
            if kind not in {"track", "recording", "song"}:
                continue
            musicbrainz_id = (
                item.get("musicbrainz_id") or item.get("musicbrainzId")
                or item.get("musicbrainz_recording_id") or item.get("recording_mbid")
                or item.get("mbid")
            )
            if not musicbrainz_id:
                continue
            artist = item.get("artist") or item.get("artist_name") or result.get("artist") or ""
            if isinstance(artist, dict):
                artist = artist.get("name", "")
            tracks.append(
                ExternalTrack(
                    provider="droppedneedle",
                    provider_id=str(musicbrainz_id),
                    title=str(item.get("title") or item.get("name") or item.get("track_name") or ""),
                    artist=str(artist),
                    album=item.get("album") or item.get("album_name"),
                    year=item.get("year") or item.get("release_year"),
                    duration=item.get("duration") or item.get("duration_seconds"),
                    cover=item.get("cover_url") or item.get("album_thumb_url") or item.get("thumb_url"),
                    available=bool(item.get("in_library", False)),
                    status=(
                        "AVAILABLE" if item.get("in_library", False)
                        else "PENDING" if item.get("requested", False)
                        else "REQUESTABLE"
                    ),
                )
            )
        # /search is a faceted endpoint in current DroppedNeedle releases and
        # can legitimately return artists/albums without a recording list.  If
        # its upstream MusicBrainz deadline expires, query the same public
        # catalogue server-side with a longer timeout.  The browser still sees
        # only Resonar; acquisition continues to be delegated to DroppedNeedle.
        return tracks or await self._search_musicbrainz(query, limit)

    async def _search_musicbrainz(self, query: str, limit: int) -> List[ExternalTrack]:
        cache_key = query.casefold().strip()
        cached = _musicbrainz_cache.get(cache_key)
        if cached and cached[0] > time.monotonic():
            return cached[1][:limit]

        global _musicbrainz_last_request_at
        try:
            async with _musicbrainz_lock:
                elapsed = time.monotonic() - _musicbrainz_last_request_at
                if elapsed < _MUSICBRAINZ_MIN_INTERVAL_SECONDS:
                    await asyncio.sleep(_MUSICBRAINZ_MIN_INTERVAL_SECONDS - elapsed)
                _musicbrainz_last_request_at = time.monotonic()
                response = await self._client.get(
                    f"{_MUSICBRAINZ_API}/recording/",
                    params={"query": query, "fmt": "json", "limit": limit},
                    headers={"User-Agent": _MUSICBRAINZ_USER_AGENT},
                    timeout=httpx.Timeout(settings.musicbrainz_timeout_seconds),
                )
            response.raise_for_status()
            recordings = response.json().get("recordings", [])
        except (httpx.HTTPError, ValueError):
            logger.warning("MusicBrainz fallback search failed", exc_info=True)
            return []

        tracks: List[ExternalTrack] = []
        for recording in recordings:
            if not isinstance(recording, dict) or not recording.get("id"):
                continue
            artist_parts = []
            artist_id = None
            for credit in recording.get("artist-credit", []):
                if isinstance(credit, dict):
                    nested_artist = credit.get("artist")
                    nested_name = nested_artist.get("name") if isinstance(nested_artist, dict) else ""
                    artist_id = nested_artist.get("id") if isinstance(nested_artist, dict) else artist_id
                    artist_parts.append(str(credit.get("name") or nested_name or ""))
                    artist_parts.append(str(credit.get("joinphrase") or ""))
            releases = recording.get("releases", [])
            release = releases[0] if isinstance(releases, list) and releases and isinstance(releases[0], dict) else {}
            release_group = release.get("release-group") if isinstance(release, dict) else {}
            length = recording.get("length")
            try:
                duration = int(int(length) / 1000) if length is not None else None
            except (TypeError, ValueError):
                duration = None
            date = release.get("date") or ""
            try:
                year = int(str(date)[:4]) if date else None
            except ValueError:
                year = None
            tracks.append(
                ExternalTrack(
                    provider="droppedneedle",
                    provider_id=str(recording["id"]),
                    title=str(recording.get("title") or ""),
                    artist="".join(artist_parts),
                    artist_id=str(artist_id) if artist_id else None,
                    album=release.get("title"),
                    album_id=str(release_group.get("id")) if isinstance(release_group, dict) and release_group.get("id") else None,
                    year=year,
                    duration=duration,
                    available=False,
                    status="REQUESTABLE",
                    metadata={"release_mbid": release.get("id")} if release.get("id") else None,
                )
            )
        if tracks:
            _musicbrainz_cache[cache_key] = (time.monotonic() + _MUSICBRAINZ_CACHE_TTL_SECONDS, tracks)
        return tracks

    async def _recording_target(self, recording_mbid: str) -> dict[str, Any]:
        """Find an edition for a recording when search results omitted it.

        DroppedNeedle v2 requires an exact MusicBrainz release for recordings
        which occur on multiple editions.  This lookup is deliberately best
        effort: the original request still works for unambiguous recordings.
        """
        global _musicbrainz_last_request_at
        try:
            async with _musicbrainz_lock:
                elapsed = time.monotonic() - _musicbrainz_last_request_at
                if elapsed < _MUSICBRAINZ_MIN_INTERVAL_SECONDS:
                    await asyncio.sleep(_MUSICBRAINZ_MIN_INTERVAL_SECONDS - elapsed)
                _musicbrainz_last_request_at = time.monotonic()
                response = await self._client.get(
                    f"{_MUSICBRAINZ_API}/recording/{recording_mbid}",
                    params={"inc": "releases+artist-credits", "fmt": "json"},
                    headers={"User-Agent": _MUSICBRAINZ_USER_AGENT},
                    timeout=httpx.Timeout(settings.musicbrainz_timeout_seconds),
                )
            response.raise_for_status()
            recording = response.json()
        except (httpx.HTTPError, ValueError):
            logger.info("Could not resolve MusicBrainz edition for recording %s", recording_mbid)
            return {}

        if not isinstance(recording, dict):
            return {}
        releases = recording.get("releases")
        release = releases[0] if isinstance(releases, list) and releases and isinstance(releases[0], dict) else {}
        release_group = release.get("release-group") if isinstance(release, dict) else {}
        artist = None
        credits = recording.get("artist-credit")
        if isinstance(credits, list):
            for credit in credits:
                nested = credit.get("artist") if isinstance(credit, dict) else None
                if isinstance(nested, dict) and nested.get("id"):
                    artist = nested["id"]
                    break
        length = recording.get("length")
        try:
            duration = int(int(length) / 1000) if length is not None else None
        except (TypeError, ValueError):
            duration = None
        return {
            "album": release.get("title") if isinstance(release, dict) else None,
            "duration": duration,
            "artist_mbid": artist,
            "release_group_mbid": release_group.get("id") if isinstance(release_group, dict) else None,
            "release_mbid": release.get("id") if isinstance(release, dict) else None,
        }

    async def request(
        self,
        *,
        type: str,
        title: str,
        artist: str,
        provider_id: Optional[str],
        album: Optional[str] = None,
        duration: Optional[int] = None,
        artist_mbid: Optional[str] = None,
        release_group_mbid: Optional[str] = None,
        release_mbid: Optional[str] = None,
    ) -> dict:
        try:
            if type == "track" and provider_id:
                # Current DroppedNeedle API: a searched recording is requested
                # by its MusicBrainz recording ID.  Its msgspec schema requires
                # the artist and title in the JSON body.  Supplying the exact
                # edition removes the ambiguity for recordings present in
                # several releases (deluxe editions, compilations, etc.).
                if not release_mbid:
                    resolved = await self._recording_target(provider_id)
                    album = album or resolved.get("album")
                    duration = duration or resolved.get("duration")
                    artist_mbid = artist_mbid or resolved.get("artist_mbid")
                    release_group_mbid = release_group_mbid or resolved.get("release_group_mbid")
                    release_mbid = resolved.get("release_mbid")
                body: dict[str, Any] = {"artist_name": artist, "track_title": title}
                optional_fields = {
                    "album_title": album,
                    "duration_seconds": duration,
                    "artist_mbid": artist_mbid,
                    "release_group_mbid": release_group_mbid,
                    "release_id": release_mbid,
                }
                body.update({key: value for key, value in optional_fields.items() if value is not None})
                response = await self._request(
                    "POST",
                    f"/api/v1/tracks/{provider_id}/request",
                    json=body,
                )
            else:
                # Backwards-compatible fallback for request types without a
                # recording MBID (albums/artists and older DN deployments).
                body = {"type": type, "title": title, "artist": artist}
                if provider_id:
                    body["musicbrainz_id"] = provider_id
                response = await self._request("POST", "/api/v1/requests/new", json=body)
            data = self._payload(response)
            task = data.get("task") or data.get("download") or {}
            task = task if isinstance(task, dict) else {}
            external_id = (
                data.get("task_id")
                or data.get("taskId")
                or data.get("id")
                or data.get("request_id")
                or task.get("task_id")
                or task.get("taskId")
                or task.get("id")
            )
            if not external_id:
                logger.warning("DroppedNeedle accepted no task identifier: %s", data)
            return {
                "accepted": bool(external_id),
                "external_id": str(external_id) if external_id else None,
                "reason": "DroppedNeedle no devolvió un identificador de descarga" if not external_id else None,
            }
        except httpx.HTTPStatusError as exc:
            response = exc.response
            detail = response.text[:500].replace("\n", " ")
            logger.warning("DroppedNeedle request rejected: status=%s body=%s", response.status_code, detail)
            return {"accepted": False, "external_id": None, "reason": f"DroppedNeedle respondió HTTP {response.status_code}"}
        except Exception:
            logger.warning("DroppedNeedle request submission failed", exc_info=True)
            return {"accepted": False, "external_id": None, "reason": "No se pudo contactar con DroppedNeedle"}

    async def get_status(self, external_id: str) -> dict:
        try:
            response = await self._request("GET", f"/api/v1/downloads/{external_id}")
            data = self._payload(response)
            data.setdefault("external_id", external_id)
            return data
        except Exception:
            logger.warning("DroppedNeedle status check failed", exc_info=True)
            return {"external_id": external_id, "state": "unknown"}

    async def cancel(self, external_id: str) -> bool:
        """Cancel the native DroppedNeedle task and its slskd transfers."""
        try:
            data = self._payload(await self._request("POST", f"/api/v1/downloads/{external_id}/cancel"))
            return bool(data.get("success"))
        except Exception:
            logger.warning("DroppedNeedle task cancellation failed", exc_info=True)
            return False

    async def get_artist_catalog(self, artist_id: str, name: Optional[str] = None) -> dict:
        data: dict[str, Any] = {}
        try:
            data = self._payload(await self._request("GET", f"/api/v1/artists/{artist_id}"))
            # Some DroppedNeedle builds acknowledge the artist but omit its
            # releases. Do not treat that partial response as a catalogue.
            if data.get("albums") or data.get("eps"):
                return data
        except Exception:
            if not name:
                logger.warning("DroppedNeedle artist lookup failed", exc_info=True)
                return await self._musicbrainz_artist_catalog(artist_id, None)
        if not name:
            fallback = await self._musicbrainz_artist_catalog(artist_id, None)
            return fallback or data
        try:
            raw = self._payload(await self._request("GET", "/api/v1/search", params={"q": name, "query": name, "limit_artists": 10, "limit_albums": 0, "buckets": "artists"}))
            candidates = raw.get("artists", []) if isinstance(raw, dict) else []
            candidate = next((item for item in candidates if isinstance(item, dict) and str(item.get("title") or item.get("name") or "").casefold() == name.casefold()), None)
            target_id = candidate.get("musicbrainz_id") if candidate else None
            resolved = self._payload(await self._request("GET", f"/api/v1/artists/{target_id}")) if target_id else {}
            if resolved.get("albums") or resolved.get("eps"):
                return resolved
        except Exception:
            logger.warning("DroppedNeedle artist resolution failed", exc_info=True)
        fallback = await self._musicbrainz_artist_catalog(artist_id, name)
        if fallback:
            # Retain any provider image rather than losing it to MusicBrainz.
            if data.get("image") or data.get("thumb_url"):
                fallback["image"] = data.get("image") or data.get("thumb_url")
            return fallback
        return data

    async def _musicbrainz_artist_catalog(self, artist_id: str, name: Optional[str]) -> dict:
        """Catalogue fallback independent of DroppedNeedle's search buckets."""
        global _musicbrainz_last_request_at
        try:
            async with _musicbrainz_lock:
                elapsed = time.monotonic() - _musicbrainz_last_request_at
                if elapsed < _MUSICBRAINZ_MIN_INTERVAL_SECONDS:
                    await asyncio.sleep(_MUSICBRAINZ_MIN_INTERVAL_SECONDS - elapsed)
                _musicbrainz_last_request_at = time.monotonic()
                mbid = artist_id
                if not re.fullmatch(r"[0-9a-fA-F-]{36}", mbid):
                    if not name:
                        return {}
                    found = await self._client.get(
                        f"{_MUSICBRAINZ_API}/artist/",
                        params={"query": f'artist:"{name}"', "fmt": "json", "limit": 5},
                        headers={"User-Agent": _MUSICBRAINZ_USER_AGENT},
                        timeout=httpx.Timeout(settings.musicbrainz_timeout_seconds),
                    )
                    found.raise_for_status()
                    candidates = found.json().get("artists", [])
                    exact = next((item for item in candidates if str(item.get("name") or "").casefold() == name.casefold()), None)
                    if not exact or not exact.get("id"):
                        return {}
                    mbid = str(exact["id"])
                response = await self._client.get(
                    f"{_MUSICBRAINZ_API}/artist/{mbid}",
                    params={"inc": "release-groups", "fmt": "json", "limit": 100},
                    headers={"User-Agent": _MUSICBRAINZ_USER_AGENT},
                    timeout=httpx.Timeout(settings.musicbrainz_timeout_seconds),
                )
            response.raise_for_status()
            artist = response.json()
        except (httpx.HTTPError, ValueError):
            logger.warning("MusicBrainz artist catalogue fallback failed for %s", artist_id, exc_info=True)
            return {}
        if not isinstance(artist, dict):
            return {}
        albums: list[dict[str, Any]] = []
        eps: list[dict[str, Any]] = []
        singles: list[dict[str, Any]] = []
        for release in artist.get("release-groups", []):
            if not isinstance(release, dict) or not release.get("id"):
                continue
            row = {
                "id": str(release["id"]),
                "title": str(release.get("title") or "Álbum sin título"),
                "year": str(release.get("first-release-date") or "")[:4] or None,
                "in_library": False,
                "requested": False,
            }
            primary = str(release.get("primary-type") or "").casefold()
            if primary == "album":
                albums.append(row)
            elif primary == "ep":
                eps.append(row)
            elif primary == "single":
                singles.append(row)
        sort_key = lambda row: (str(row.get("year") or "9999"), str(row["title"]).casefold())
        return {
            "musicbrainz_id": str(artist.get("id") or artist_id),
            "name": str(artist.get("name") or name or "Artista"),
            "albums": sorted(albums, key=sort_key),
            "eps": sorted(eps, key=sort_key),
            "singles": singles,
        }

    async def get_album_catalog(self, album_id: str, artist: Optional[str] = None, title: Optional[str] = None) -> dict:
        try:
            return self._payload(await self._request("GET", f"/api/v1/albums/{album_id}"))
        except Exception:
            if not title:
                logger.warning("DroppedNeedle album lookup failed", exc_info=True)
                return {}
        try:
            query = f"{artist or ''} {title}".strip()
            raw = self._payload(await self._request("GET", "/api/v1/search", params={"q": query, "query": query, "limit_artists": 0, "limit_albums": 20, "buckets": "albums"}))
            candidates = raw.get("albums", []) if isinstance(raw, dict) else []
            candidate = next((item for item in candidates if isinstance(item, dict) and str(item.get("title") or "").casefold() == title.casefold() and (not artist or str(item.get("artist") or "").casefold() == artist.casefold())), None)
            target_id = candidate.get("musicbrainz_id") if candidate else None
            return self._payload(await self._request("GET", f"/api/v1/albums/{target_id}")) if target_id else {}
        except Exception:
            logger.warning("DroppedNeedle album resolution failed", exc_info=True)
            return {}

    async def request_album(
        self, *, musicbrainz_id: str, artist: str, album: str, year: Optional[int], artist_mbid: Optional[str]
    ) -> dict:
        body: dict[str, Any] = {"musicbrainz_id": musicbrainz_id, "artist": artist, "album": album}
        if year is not None:
            body["year"] = year
        if artist_mbid:
            body["artist_mbid"] = artist_mbid
        try:
            return self._payload(await self._request("POST", "/api/v1/requests/new", json=body))
        except Exception:
            logger.warning("DroppedNeedle album request failed", exc_info=True)
            return {}

    async def request_albums(self, items: List[dict]) -> dict:
        try:
            return self._payload(await self._request("POST", "/api/v1/requests/batch", json={"items": items}))
        except Exception:
            logger.warning("DroppedNeedle batch album request failed", exc_info=True)
            return {}

    async def aclose(self) -> None:
        await self._client.aclose()


def get_droppedneedle_client():
    if settings.mock_external_services:
        return MockDroppedNeedleClient()
    return RealDroppedNeedleClient()
