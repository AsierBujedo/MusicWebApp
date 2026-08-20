"""slskd integration.

slskd exposes a documented REST API under ``/api/v0``. We use it only for
health and download/transfer status; the USER never talks to slskd directly and
the API key is never exposed to the browser.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

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

    async def reset_download_queue(self) -> dict[str, int | bool]:
        """Cancel every slskd download and restart its application process.

        This intentionally manages the whole slskd queue, including transfers
        not created by Resonar. It is reachable only from the admin endpoint.
        """
        if not self._base:
            raise RuntimeError("slskd no está configurado")
        try:
            response = await self._client.get("/api/v0/transfers/downloads")
            response.raise_for_status()
            transfers = response.json()
            entries = self._download_entries(transfers)

            results = await asyncio.gather(
                *(
                    self._client.delete(f"/api/v0/transfers/downloads/{username}/{transfer_id}")
                    for username, transfer_id in entries
                ),
                return_exceptions=True,
            )
            cancelled = sum(1 for result in results if not isinstance(result, Exception) and result.status_code < 400)
            failed = len(entries) - cancelled

            # Clear the completed records too, then ask slskd itself to restart.
            completed = await self._client.delete("/api/v0/transfers/downloads/all/completed")
            completed.raise_for_status()
            restarted = await self._client.put("/api/v0/application")
            # Queue maintenance can be permitted for a restricted key while
            # restarting the application requires Administrator. Report the
            # successful cleanup accurately instead of turning it into a 502.
            if restarted.status_code in {401, 403}:
                logger.warning("slskd queue cleared but restart was not authorized")
                return {"cancelled": cancelled, "failed": failed, "restarted": False}
            restarted.raise_for_status()
            return {"cancelled": cancelled, "failed": failed, "restarted": True}
        except Exception:
            logger.warning("slskd queue reset failed", exc_info=True)
            raise

    @staticmethod
    def _download_entries(payload: Any) -> list[tuple[str, str]]:
        """Normalise the grouped and flat transfer shapes used by slskd."""
        if isinstance(payload, list):
            groups = payload
        elif isinstance(payload, dict):
            groups = payload.get("items") or payload.get("downloads") or [payload]
        else:
            groups = []
        entries: list[tuple[str, str]] = []
        for group in groups if isinstance(groups, list) else []:
            if not isinstance(group, dict):
                continue
            username = group.get("username")
            files = group.get("files") or group.get("downloads") or group.get("transfers") or []
            if not isinstance(files, list):
                files = [group]
            for item in files:
                if not isinstance(item, dict):
                    continue
                transfer_id = item.get("id") or item.get("filename") or item.get("localFilename")
                item_username = item.get("username") or username
                if item_username and transfer_id:
                    entries.append((str(item_username), str(transfer_id)))
        return list(dict.fromkeys(entries))

    async def aclose(self) -> None:
        await self._client.aclose()


def get_slskd_client():
    if settings.mock_external_services:
        return MockSlskdClient()
    return RealSlskdClient()
