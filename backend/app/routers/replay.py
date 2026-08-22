"""Replay catalogue and Jellyfin streaming proxy."""
from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from starlette.background import BackgroundTask
from starlette.responses import Response, StreamingResponse

from app.core.features import require_feature
from app.dependencies import get_current_user
from app.models.user import User
from app.services.replay_service import ReplayServiceError, get_replay_service

router = APIRouter(prefix="/api/replay", tags=["replay"])


def _replay_user(user: User = Depends(get_current_user)) -> User:
    require_feature(user, "replay.access")
    return user


def _error(exc: Exception) -> HTTPException:
    if isinstance(exc, ReplayServiceError):
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 404:
        return HTTPException(status_code=404, detail="Contenido no encontrado")
    return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="No se pudo conectar con Jellyfin")


@router.get("/status")
async def replay_status(_user: User = Depends(_replay_user)):
    return {"configured": get_replay_service().configured}


@router.get("/items")
async def replay_items(_user: User = Depends(_replay_user)):
    try:
        return await get_replay_service().library()
    except Exception as exc:
        raise _error(exc) from exc


@router.get("/items/{item_id}")
async def replay_item(item_id: str, _user: User = Depends(_replay_user)):
    try:
        result = await get_replay_service().item(item_id)
    except Exception as exc:
        raise _error(exc) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Contenido no encontrado")
    return result


@router.get("/items/{item_id}/image")
async def replay_image(item_id: str, _user: User = Depends(_replay_user)):
    service = get_replay_service()
    try:
        response = await service.image(item_id)
    except Exception as exc:
        raise _error(exc) from exc
    return Response(content=response.content, media_type=response.headers.get("content-type", "image/jpeg"), headers={"Cache-Control": "private, max-age=86400"})


@router.get("/items/{item_id}/stream")
async def replay_stream(item_id: str, request: Request, _user: User = Depends(_replay_user)):
    service = get_replay_service()
    try:
        response = await service.stream(item_id, request.headers.get("range"))
        response.raise_for_status()
    except Exception as exc:
        raise _error(exc) from exc
    headers = {key: value for key, value in response.headers.items() if key.lower() in {"accept-ranges", "content-length", "content-range", "content-type"}}
    return StreamingResponse(response.aiter_bytes(), status_code=response.status_code, headers=headers, media_type=response.headers.get("content-type", "video/mp4"), background=BackgroundTask(response.aclose))
