"""Music request lifecycle service.

A "music request" is a user asking the system to acquire a track that is not yet
in the local library. The lifecycle is:

    pending -> searching -> downloading -> processing -> completed
                                              \-> failed

State transitions are driven by a background worker (see worker.py) that polls
the acquisition backend (slskd / DroppedNeedle). Every transition emits a
realtime event so connected clients update instantly.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.events import event_manager
from ..models.music_request import MusicRequest, RequestStatus
from ..models.user import User


VALID_TRANSITIONS = {
    RequestStatus.pending: {RequestStatus.searching, RequestStatus.failed, RequestStatus.cancelled},
    RequestStatus.searching: {RequestStatus.downloading, RequestStatus.failed, RequestStatus.cancelled},
    RequestStatus.downloading: {RequestStatus.processing, RequestStatus.failed, RequestStatus.cancelled},
    RequestStatus.processing: {RequestStatus.completed, RequestStatus.failed},
    RequestStatus.completed: set(),
    RequestStatus.failed: {RequestStatus.pending},  # allow retry
    RequestStatus.cancelled: {RequestStatus.pending},
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_request(db: Session, *, user: User, query: str, artist: Optional[str], title: Optional[str]) -> MusicRequest:
    req = MusicRequest(
        user_id=user.id,
        query=query.strip(),
        artist=(artist or "").strip() or None,
        title=(title or "").strip() or None,
        status=RequestStatus.pending,
        progress=0,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    event_manager.publish_threadsafe(
        "request.created",
        {"request": req.to_public()},
        user_id=user.id,
    )
    return req


def list_requests(db: Session, *, user: User, include_all: bool = False) -> List[MusicRequest]:
    stmt = select(MusicRequest).order_by(MusicRequest.created_at.desc())
    if not include_all:
        stmt = stmt.where(MusicRequest.user_id == user.id)
    return list(db.scalars(stmt).all())


def get_request(db: Session, request_id: str) -> Optional[MusicRequest]:
    return db.get(MusicRequest, request_id)


def transition(
    db: Session,
    req: MusicRequest,
    new_status: RequestStatus,
    *,
    progress: Optional[int] = None,
    message: Optional[str] = None,
    track_id: Optional[str] = None,
) -> MusicRequest:
    """Move a request to a new status, validating the transition, and emit an event."""
    if new_status != req.status and new_status not in VALID_TRANSITIONS.get(req.status, set()):
        raise ValueError(f"Invalid transition {req.status} -> {new_status}")

    req.status = new_status
    if progress is not None:
        req.progress = max(0, min(100, progress))
    if message is not None:
        req.message = message
    if track_id is not None:
        req.result_track_id = track_id
    if new_status == RequestStatus.completed:
        req.progress = 100
        req.completed_at = _now()
    req.updated_at = _now()
    db.commit()
    db.refresh(req)

    event_manager.publish_threadsafe(
        "request.updated",
        {"request": req.to_public()},
        user_id=req.user_id,
    )
    return req


def cancel_request(db: Session, req: MusicRequest) -> MusicRequest:
    if req.status in {RequestStatus.completed, RequestStatus.cancelled}:
        return req
    return transition(db, req, RequestStatus.cancelled, message="Cancelled by user")


def retry_request(db: Session, req: MusicRequest) -> MusicRequest:
    if req.status not in {RequestStatus.failed, RequestStatus.cancelled}:
        raise ValueError("Only failed or cancelled requests can be retried")
    req.progress = 0
    req.message = None
    return transition(db, req, RequestStatus.pending, message="Re-queued")
