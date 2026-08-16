"""In-memory realtime event manager backing the SSE endpoint.

Each connected client gets an ``asyncio.Queue``. Events are published with an
audience (a set of user IDs allowed to receive them, or ``None`` for broadcast
to every admin). This is deliberately simple and process-local; the public
surface (``publish`` / ``subscribe``) can be reimplemented on Redis pub/sub
later without touching callers.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Set


@dataclass
class Subscriber:
    user_id: str
    is_admin: bool
    queue: "asyncio.Queue[dict]" = field(default_factory=lambda: asyncio.Queue(maxsize=100))


class EventManager:
    def __init__(self) -> None:
        self._subscribers: Set[Subscriber] = set()
        self._lock = asyncio.Lock()

    async def subscribe(self, user_id: str, is_admin: bool) -> Subscriber:
        sub = Subscriber(user_id=user_id, is_admin=is_admin)
        async with self._lock:
            self._subscribers.add(sub)
        return sub

    async def unsubscribe(self, sub: Subscriber) -> None:
        async with self._lock:
            self._subscribers.discard(sub)

    async def publish(
        self,
        event: Dict[str, Any],
        *,
        audience_user_ids: Optional[Set[str]] = None,
        include_admins: bool = True,
    ) -> None:
        """Deliver ``event`` to matching subscribers.

        - ``audience_user_ids``: only these users receive it. ``None`` means the
          event carries no private data and can go to everyone.
        - ``include_admins``: admins additionally receive the event (they have a
          legitimate operational view of all requests).
        """
        async with self._lock:
            targets = list(self._subscribers)
        for sub in targets:
            allowed = (
                audience_user_ids is None
                or sub.user_id in audience_user_ids
                or (include_admins and sub.is_admin)
            )
            if not allowed:
                continue
            try:
                sub.queue.put_nowait(event)
            except asyncio.QueueFull:
                # Slow client; drop the frame rather than block the publisher.
                pass

    def publish_threadsafe(
        self,
        loop: asyncio.AbstractEventLoop,
        event: Dict[str, Any],
        *,
        audience_user_ids: Optional[Set[str]] = None,
        include_admins: bool = True,
    ) -> None:
        """Publish from a non-async context (e.g. a worker thread)."""
        asyncio.run_coroutine_threadsafe(
            self.publish(event, audience_user_ids=audience_user_ids, include_admins=include_admins),
            loop,
        )


# Process-wide singleton.
event_manager = EventManager()
