"""Jellyfin adapter used by the Replay product module.

Replay deliberately keeps Jellyfin credentials and item identifiers behind the
Resonar backend. The browser only ever sees same-origin `/api/replay/*` URLs.
"""
from __future__ import annotations

import time
from typing import Any

import httpx

from app.config import settings


class ReplayServiceError(Exception):
    pass


class ReplayService:
    def __init__(self) -> None:
        self._base = settings.jellyfin_url.rstrip("/")
        self._client = httpx.AsyncClient(base_url=self._base, timeout=30.0)
        self._token: str | None = None
        self._user_id: str | None = None
        self._expires_at = 0.0

    @property
    def configured(self) -> bool:
        return bool(self._base and settings.jellyfin_username and settings.jellyfin_password)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _authenticate(self) -> None:
        if not self.configured:
            raise ReplayServiceError("Replay todavía no está configurado")
        if self._token and self._user_id and self._expires_at > time.monotonic():
            return
        response = await self._client.post(
            "/Users/AuthenticateByName",
            json={"Username": settings.jellyfin_username, "Pw": settings.jellyfin_password},
            headers={
                "X-Emby-Authorization": 'MediaBrowser Client="Resonar Replay", Device="Resonar", DeviceId="resonar-replay", Version="1.0"'
            },
        )
        response.raise_for_status()
        payload = response.json()
        user = payload.get("User") if isinstance(payload, dict) else None
        token = payload.get("AccessToken") if isinstance(payload, dict) else None
        if not isinstance(user, dict) or not user.get("Id") or not isinstance(token, str):
            raise ReplayServiceError("Jellyfin devolvió una sesión inválida")
        self._user_id = str(user["Id"])
        self._token = token
        self._expires_at = time.monotonic() + 3_600

    async def _headers(self) -> dict[str, str]:
        await self._authenticate()
        return {"X-Emby-Token": self._token or ""}

    @staticmethod
    def _item(raw: dict[str, Any]) -> dict[str, Any]:
        item_id = str(raw.get("Id") or "")
        runtime_ticks = raw.get("RunTimeTicks")
        runtime_minutes = round(int(runtime_ticks) / 600_000_000) if isinstance(runtime_ticks, int) else None
        return {
            "id": item_id,
            "title": str(raw.get("Name") or "Sin título"),
            "type": str(raw.get("Type") or "Video"),
            "overview": raw.get("Overview"),
            "year": str(raw.get("ProductionYear") or raw.get("PremiereDate", "")[:4] or "") or None,
            "rating": raw.get("CommunityRating"),
            "runtimeMinutes": runtime_minutes,
            "seriesName": raw.get("SeriesName"),
            "season": raw.get("ParentIndexNumber"),
            "episode": raw.get("IndexNumber"),
            "hasImage": bool((raw.get("ImageTags") or {}).get("Primary")),
        }

    async def library(self) -> list[dict[str, Any]]:
        headers = await self._headers()
        response = await self._client.get(
            f"/Users/{self._user_id}/Items",
            headers=headers,
            params={
                "IncludeItemTypes": "Movie,Series,Episode",
                "Recursive": "true",
                "Fields": "Overview,PremiereDate,ProductionYear,CommunityRating,RunTimeTicks,ImageTags,SeriesName,ParentIndexNumber,IndexNumber",
                "SortBy": "DateCreated,SortName",
                "SortOrder": "Descending",
                "Limit": 250,
            },
        )
        response.raise_for_status()
        payload = response.json()
        items = payload.get("Items", []) if isinstance(payload, dict) else []
        return [self._item(item) for item in items if isinstance(item, dict) and item.get("Id")]

    async def item(self, item_id: str) -> dict[str, Any] | None:
        headers = await self._headers()
        response = await self._client.get(f"/Users/{self._user_id}/Items/{item_id}", headers=headers)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        payload = response.json()
        return self._item(payload) if isinstance(payload, dict) else None

    async def image(self, item_id: str) -> httpx.Response:
        headers = await self._headers()
        response = await self._client.get(f"/Items/{item_id}/Images/Primary", headers=headers)
        response.raise_for_status()
        return response

    async def stream(self, item_id: str, range_header: str | None) -> httpx.Response:
        headers = await self._headers()
        if range_header:
            headers["Range"] = range_header
        request = self._client.build_request("GET", f"/Videos/{item_id}/stream", params={"static": "true"}, headers=headers)
        return await self._client.send(request, stream=True)


_service: ReplayService | None = None


def get_replay_service() -> ReplayService:
    global _service
    if _service is None:
        _service = ReplayService()
    return _service
