"""DroppedNeedle API v1 integration.

DroppedNeedle owns discovery and acquisition. Its bearer token is held only by
this backend; slskd remains a DroppedNeedle dependency, not a second download
orchestrator for this application.
"""
from __future__ import annotations

import logging
from typing import Any, List, Optional

import httpx

from app.config import settings
from app.services.integrations.base import ExternalTrack, HealthResult
from app.services.integrations.mocks import MockDroppedNeedleClient

logger = logging.getLogger(__name__)


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
            response = await self._request("GET", "/api/v1/search", params={"q": query})
            payload = self._payload(response)
        except Exception:
            logger.warning("DroppedNeedle search failed", exc_info=True)
            return []

        results = payload.get("results", payload.get("items", []))
        if not isinstance(results, list):
            return []
        tracks: List[ExternalTrack] = []
        for result in results[:limit]:
            if not isinstance(result, dict):
                continue
            musicbrainz_id = result.get("musicbrainz_id") or result.get("musicbrainzId")
            if not musicbrainz_id or result.get("type", "track") not in {"track", "recording"}:
                continue
            tracks.append(
                ExternalTrack(
                    provider="droppedneedle",
                    provider_id=str(musicbrainz_id),
                    title=str(result.get("title") or ""),
                    artist=str(result.get("artist") or ""),
                    album=result.get("album"),
                    year=result.get("year"),
                    duration=result.get("duration"),
                    cover=result.get("cover_url") or result.get("album_thumb_url") or result.get("thumb_url"),
                    available=bool(result.get("in_library", False)),
                    status=(
                        "AVAILABLE" if result.get("in_library", False)
                        else "PENDING" if result.get("requested", False)
                        else "REQUESTABLE"
                    ),
                )
            )
        return tracks

    async def request(self, *, type: str, title: str, artist: str, provider_id: Optional[str]) -> dict:
        body = {"type": type, "title": title, "artist": artist}
        if provider_id:
            body["musicbrainz_id"] = provider_id
        try:
            response = await self._request("POST", "/api/v1/requests/new", json=body)
            data = self._payload(response)
            external_id = data.get("task_id") or data.get("taskId") or data.get("id") or data.get("request_id")
            return {"accepted": bool(external_id), "external_id": str(external_id) if external_id else None, "raw": data}
        except Exception:
            logger.warning("DroppedNeedle request submission failed", exc_info=True)
            return {"accepted": False, "external_id": None}

    async def get_status(self, external_id: str) -> dict:
        try:
            response = await self._request("GET", f"/api/v1/downloads/{external_id}")
            data = self._payload(response)
            data.setdefault("external_id", external_id)
            return data
        except Exception:
            logger.warning("DroppedNeedle status check failed", exc_info=True)
            return {"external_id": external_id, "state": "unknown"}

    async def aclose(self) -> None:
        await self._client.aclose()


def get_droppedneedle_client():
    if settings.mock_external_services:
        return MockDroppedNeedleClient()
    return RealDroppedNeedleClient()
