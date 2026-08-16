"""Realtime updates over Server-Sent Events: GET /api/events

Each connected client gets a per-user subscription. Frames are JSON-encoded
``RealtimeEvent`` objects. A periodic comment line keeps proxies from closing
idle connections. The browser's ``EventSource`` auto-reconnects on drop.
"""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.core.events import event_manager
from app.core.permissions import is_admin
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api", tags=["events"])

# Send a heartbeat comment at least this often (seconds).
_HEARTBEAT_SECONDS = 20


@router.get("/events")
async def events(request: Request, user: User = Depends(get_current_user)):
    subscriber = await event_manager.subscribe(user.id, is_admin(user))

    async def event_stream():
        try:
            # Prime the stream so the client's connection opens immediately.
            yield ": connected\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(subscriber.queue.get(), timeout=_HEARTBEAT_SECONDS)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        finally:
            await event_manager.unsubscribe(subscriber)

    headers = {
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",  # disable proxy buffering (nginx)
    }
    return StreamingResponse(event_stream(), media_type="text/event-stream", headers=headers)
