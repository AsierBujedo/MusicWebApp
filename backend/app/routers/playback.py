"""Synchronise playback between a user's active Resonar sessions."""
from typing import Any
from fastapi import APIRouter, Body, Depends
from app.core.events import event_manager
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/playback", tags=["playback"])

@router.post("/sync", status_code=204)
async def sync(payload: dict[str, Any] = Body(...), user: User = Depends(get_current_user)):
    track = payload.get("track")
    queue = payload.get("queue")
    source_id = payload.get("sourceId")
    if not isinstance(track, dict) or not isinstance(queue, list) or not isinstance(source_id, str):
        return
    await event_manager.publish({"type": "playback.sync", "track": track, "queue": queue[:200], "isPlaying": bool(payload.get("isPlaying")), "sourceId": source_id}, audience_user_ids={user.id})
