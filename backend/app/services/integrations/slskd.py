"""slskd integration.

slskd exposes a documented REST API under ``/api/v0``. We use it only for
health and download/transfer status; the USER never talks to slskd directly and
the API key is never exposed to the browser.
"""
from __future__ import annotations

import logging

import httpx

from app.config import settings
from app.services.integrations.base import HealthResult
from app.services.integrations.mocks import MockSlskdClient

logger = logging.getLogger(__name__)


class RealSlskdClient:
    def __init__(self) -> None:
        self._base = settings.slskd_url.rstrip("/")
        headers = {}
        if settings.slskd_api_key:
            headers["X-API-Key"] = settings.slskd_api_key
        self._client = httpx.AsyncClient(base_url=self._base, headers=headers, timeout=10.0)

    async def health(self) -> HealthResult:
        if not self._base:
            return "offline", "Sin configurar"
        try:
            # slskd exposes /health returning "Healthy".
            resp = await self._client.get("/health")
            if resp.status_code < 400:
                return "online", "Conectado"
            return "degraded", f"HTTP {resp.status_code}"
        except Exception:
            logger.warning("slskd health check failed", exc_info=True)
            return "offline", "No responde"

    async def get_download_status(self, external_id: str) -> dict:
        try:
            resp = await self._client.get("/api/v0/transfers/downloads")
            resp.raise_for_status()
            return {"external_id": external_id, "downloads": resp.json()}
        except Exception:
            logger.warning("slskd download status failed", exc_info=True)
            return {"external_id": external_id, "state": "unknown"}

    async def aclose(self) -> None:
        await self._client.aclose()


def get_slskd_client():
    if settings.mock_external_services:
        return MockSlskdClient()
    return RealSlskdClient()
