"""DroppedNeedle integration.

DroppedNeedle handles music discovery / acquisition requests. Its exact HTTP
surface is deployment-specific, so this adapter keeps the routes configurable
and documents the expected shapes rather than inventing endpoints that pretend
to work. The mock implementation is used by default and in tests.

Expected (configurable) endpoints — adjust to your DroppedNeedle deployment:
- GET  {DROPPEDNEEDLE_URL}/health          -> 200 when healthy
- GET  {DROPPEDNEEDLE_URL}/search?q=...     -> {"results": [ {title, artist, ...} ]}
- POST {DROPPEDNEEDLE_URL}/requests         -> {"id": "...", "status": "..."}
- GET  {DROPPEDNEEDLE_URL}/requests/{id}    -> {"status": "...", "progress": n}

Auth is sent via the ``X-API-Key`` header from ``DROPPEDNEEDLE_API_KEY``.
"""
from __future__ import annotations

import logging
from typing import List, Optional

import httpx

from app.config import settings
from app.services.integrations.base import ExternalTrack, HealthResult
from app.services.integrations.mocks import MockDroppedNeedleClient

logger = logging.getLogger(__name__)


class RealDroppedNeedleClient:
    def __init__(self) -> None:
        self._base = settings.droppedneedle_url.rstrip("/")
        headers = {}
        if settings.droppedneedle_api_key:
            headers["X-API-Key"] = settings.droppedneedle_api_key
        self._client = httpx.AsyncClient(base_url=self._base, headers=headers, timeout=15.0)

    async def health(self) -> HealthResult:
        if not self._base:
            return "offline", "Sin configurar"
        try:
            resp = await self._client.get("/health")
            if resp.status_code < 400:
                return "online", "Conectado"
            return "degraded", f"HTTP {resp.status_code}"
        except Exception:
            logger.warning("DroppedNeedle health check failed", exc_info=True)
            return "offline", "No responde"

    async def search(self, query: str, limit: int) -> List[ExternalTrack]:
        try:
            resp = await self._client.get("/search", params={"q": query, "limit": limit})
            resp.raise_for_status()
            payload = resp.json()
        except Exception:
            logger.warning("DroppedNeedle search failed", exc_info=True)
            return []

        results = payload.get("results", payload if isinstance(payload, list) else [])
        tracks: List[ExternalTrack] = []
        for r in results[:limit]:
            tracks.append(
                ExternalTrack(
                    provider="droppedneedle",
                    provider_id=str(r.get("id") or r.get("providerId") or ""),
                    title=r.get("title", ""),
                    artist=r.get("artist", ""),
                    album=r.get("album"),
                    year=r.get("year"),
                    duration=r.get("duration"),
                    cover=r.get("cover"),
                    available=False,  # not yet in the library; it is requestable
                )
            )
        return tracks

    async def request(self, *, type: str, title: str, artist: str, provider_id: Optional[str]) -> dict:
        try:
            resp = await self._client.post(
                "/requests",
                json={"type": type, "title": title, "artist": artist, "providerId": provider_id},
            )
            resp.raise_for_status()
            data = resp.json()
            return {"accepted": True, "external_id": str(data.get("id", "")), "raw": data}
        except Exception:
            logger.warning("DroppedNeedle request submission failed", exc_info=True)
            return {"accepted": False, "external_id": None}

    async def get_status(self, external_id: str) -> dict:
        try:
            resp = await self._client.get(f"/requests/{external_id}")
            resp.raise_for_status()
            return resp.json()
        except Exception:
            logger.warning("DroppedNeedle status check failed", exc_info=True)
            return {"external_id": external_id, "state": "unknown"}

    async def aclose(self) -> None:
        await self._client.aclose()


def get_droppedneedle_client():
    if settings.mock_external_services:
        return MockDroppedNeedleClient()
    return RealDroppedNeedleClient()
