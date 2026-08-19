r"""Music request lifecycle (pure DB logic).

A *request* is a user asking the system to acquire something not yet available
locally. Lifecycle (matching the frontend ``RequestStatus`` contract):

    PENDING -> APPROVED -> SEARCHING -> DOWNLOADING -> AVAILABLE
       |            \-------------------------------\-> FAILED
       \-> REJECTED

Admins move PENDING -> APPROVED / REJECTED. A background worker then drives
APPROVED -> SEARCHING -> DOWNLOADING -> AVAILABLE (or FAILED). This module only
mutates rows and validates transitions; realtime events are emitted by the
callers (routers / worker) so the DB layer stays synchronous and framework-free.
"""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.models.base import utcnow
from app.models.music_request import MusicRequest
from app.models.track import Track
from app.models.user import User

# Statuses where the request is still being worked on.
ACTIVE_STATUSES = {"PENDING", "APPROVED", "SEARCHING", "DOWNLOADING"}
TERMINAL_STATUSES = {"AVAILABLE", "FAILED", "REJECTED"}

VALID_TRANSITIONS = {
    "PENDING": {"APPROVED", "REJECTED", "FAILED"},
    "APPROVED": {"SEARCHING", "FAILED"},
    "SEARCHING": {"DOWNLOADING", "FAILED"},
    "DOWNLOADING": {"AVAILABLE", "FAILED"},
    "AVAILABLE": set(),
    "REJECTED": {"PENDING"},  # retry
    "FAILED": {"PENDING"},  # retry
}


class RequestError(Exception):
    """Domain error mapped to HTTP 400/409 by callers."""


def create_request(db: DbSession, *, user: User, type_: str, track: Track) -> MusicRequest:
    """Create a request for ``track`` on behalf of ``user``.

    Idempotent per (user, track): an already-active request is returned instead
    of creating a duplicate."""
    existing = db.scalar(
        select(MusicRequest).where(
            MusicRequest.requested_by == user.id,
            MusicRequest.track_id == track.id,
            MusicRequest.status.in_(ACTIVE_STATUSES),
        )
    )
    if existing is not None:
        return existing

    req = MusicRequest(
        requested_by=user.id,
        type=type_,
        track_id=track.id,
        title=track.title,
        artist=track.artist,
        cover=track.cover,
        status="APPROVED" if user.auto_approve_requests else "PENDING",
        progress=None,
        # Results from DroppedNeedle are persisted behind local opaque track
        # IDs. Its identifier is a MusicBrainz ID for requestable entries.
        musicbrainz_id=track.provider_id if track.provider == "droppedneedle" else None,
    )
    db.add(req)

    # Reflect the pending acquisition on the track itself.
    track.status = "PENDING"
    track.progress = None
    track.updated_at = utcnow()

    db.commit()
    db.refresh(req)
    return req


def list_requests(db: DbSession, *, user: Optional[User] = None) -> List[MusicRequest]:
    """List requests. Scoped to ``user`` when given, otherwise all (admin view)."""
    stmt = select(MusicRequest).order_by(MusicRequest.created_at.desc())
    if user is not None:
        stmt = stmt.where(MusicRequest.requested_by == user.id)
    return list(db.scalars(stmt).all())


def get_request(db: DbSession, request_id: str) -> Optional[MusicRequest]:
    return db.get(MusicRequest, request_id)


def delete_request(db: DbSession, req: MusicRequest) -> None:
    track = db.get(Track, req.track_id)
    db.delete(req)
    db.flush()
    # Do not leave a catalogue item permanently pending when its final local
    # request was removed. A remote DroppedNeedle task is intentionally not
    # cancelled here because API v1 cancellation is deployment/version specific.
    other_active = db.scalar(
        select(MusicRequest.id).where(
            MusicRequest.track_id == req.track_id,
            MusicRequest.status.in_(ACTIVE_STATUSES),
        ).limit(1)
    )
    if track is not None and other_active is None and track.status in {"PENDING", "DOWNLOADING"}:
        track.status = "REQUESTABLE"
        track.available = False
        track.progress = None
    db.commit()


def transition(
    db: DbSession,
    req: MusicRequest,
    new_status: str,
    *,
    progress: Optional[int] = None,
    error_message: Optional[str] = None,
) -> MusicRequest:
    """Validate and apply a status change. Raises ``RequestError`` if illegal."""
    if new_status != req.status and new_status not in VALID_TRANSITIONS.get(req.status, set()):
        raise RequestError(f"Invalid transition {req.status} -> {new_status}")

    req.status = new_status
    if progress is not None:
        req.progress = max(0, min(100, progress))
    if new_status == "DOWNLOADING" and req.progress is None:
        req.progress = 0
    if new_status in TERMINAL_STATUSES:
        req.progress = 100 if new_status == "AVAILABLE" else req.progress
    req.error_message = error_message
    req.updated_at = utcnow()
    db.commit()
    db.refresh(req)
    return req


def retry(db: DbSession, req: MusicRequest) -> MusicRequest:
    if req.status not in {"FAILED", "REJECTED"}:
        raise RequestError("Only failed or rejected requests can be retried")
    req.progress = None
    req.error_message = None
    return transition(db, req, "PENDING")
