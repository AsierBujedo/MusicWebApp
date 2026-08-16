"""Thin helpers to build and publish the two realtime event shapes the frontend
understands (``request.updated`` and ``track.updated``) with correct audience
scoping so users never receive other users' private events."""
from __future__ import annotations

from typing import Optional, Set

from app.core.events import event_manager


async def emit_request_updated(
    *, request_id: str, status: str, progress: Optional[int], owner_user_id: str
) -> None:
    event = {"type": "request.updated", "requestId": request_id, "status": status}
    if progress is not None:
        event["progress"] = progress
    # Owner receives it; admins also receive it (operational view).
    await event_manager.publish(event, audience_user_ids={owner_user_id}, include_admins=True)


async def emit_track_updated(
    *, track_id: str, status: str, progress: Optional[int], audience_user_ids: Optional[Set[str]]
) -> None:
    event = {"type": "track.updated", "trackId": track_id, "status": status}
    if progress is not None:
        event["progress"] = progress
    await event_manager.publish(event, audience_user_ids=audience_user_ids, include_admins=True)
