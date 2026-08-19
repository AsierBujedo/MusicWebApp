"""Authenticated cover-art proxy for Navidrome."""
from __future__ import annotations

import json

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask
from sqlalchemy.orm import Session as DbSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services import library_service
from app.services.integrations import get_navidrome_client

router = APIRouter(prefix="/api", tags=["covers"])


@router.get("/covers/{track_id}")
async def cover(
    track_id: str,
    _user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    track = library_service.get_track(db, track_id)
    if track is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cover not found")

    if track.provider == "droppedneedle":
        try:
            release_mbid = json.loads(track.metadata_json or "{}").get("release_mbid")
        except (TypeError, ValueError):
            release_mbid = None
        if not release_mbid:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cover not found")
        client = httpx.AsyncClient(timeout=httpx.Timeout(15.0), follow_redirects=True)
        try:
            response = await client.send(
                client.build_request("GET", f"https://coverartarchive.org/release/{release_mbid}/front-250"),
                stream=True,
            )
        except httpx.HTTPError:
            await client.aclose()
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Cover service unavailable")
        if response.status_code >= 400:
            await response.aclose()
            await client.aclose()
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cover not found")

        async def musicbrainz_body():
            try:
                async for chunk in response.aiter_bytes():
                    yield chunk
            finally:
                await response.aclose()

        headers = {"Cache-Control": "public, max-age=86400"}
        if "content-length" in response.headers:
            headers["Content-Length"] = response.headers["content-length"]
        return StreamingResponse(
            musicbrainz_body(),
            headers=headers,
            media_type=response.headers.get("content-type", "image/jpeg"),
            background=BackgroundTask(client.aclose),
        )

    if track.provider != "navidrome" or not track.provider_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cover not found")

    navidrome = get_navidrome_client()
    try:
        song = await navidrome.get_track(track.provider_id)
        if song is None or not song.cover_id:
            await navidrome.aclose()
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cover not found")
        handle = await navidrome.open_cover(song.cover_id)
        if handle.status_code >= 400:
            await navidrome.aclose()
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cover not found")
    except HTTPException:
        raise
    except Exception:
        await navidrome.aclose()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Cover service unavailable")

    return StreamingResponse(
        handle.body,
        status_code=handle.status_code,
        headers=handle.headers,
        media_type=handle.headers.get("Content-Type", "image/jpeg"),
        background=BackgroundTask(navidrome.aclose),
    )
