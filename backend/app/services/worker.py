"""Background worker that advances music-request acquisition.

It polls active requests on a fixed interval and drives the lifecycle:

    APPROVED -> SEARCHING -> DOWNLOADING (0..100) -> AVAILABLE

Every transition emits a realtime ``request.updated`` frame to the owner (and
admins). When a request reaches ``AVAILABLE`` the underlying track is flipped to
``AVAILABLE`` and a ``track.updated`` frame is emitted so any open search view
updates instantly.

In mock mode the progress is simulated. Against a real DroppedNeedle/slskd
deployment, ``_poll_progress`` is where you would read true transfer state.
"""
from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models.music_request import MusicRequest
from app.models.track import Track
from app.services import event_service, request_service
from app.services.integrations import get_droppedneedle_client

logger = logging.getLogger(__name__)

# How much simulated progress to add per poll while downloading (mock mode only).
_PROGRESS_STEP = 25


async def _advance_once() -> None:
    """Run a single pass over active requests. Uses a short-lived DB session.

    In mock mode the lifecycle is simulated. Against real services we reconcile
    against DroppedNeedle's active-requests/downloads state.
    """
    db = SessionLocal()
    try:
        active = list(
            db.scalars(
                select(MusicRequest).where(
                    MusicRequest.status.in_(["APPROVED", "SEARCHING", "DOWNLOADING"])
                )
            ).all()
        )
        if not active:
            return

        if settings.mock_external_services:
            for req in active:
                try:
                    await _advance_request(db, req)
                except Exception:
                    logger.exception("Failed advancing request %s", req.id)
                    db.rollback()
        else:
            await _reconcile_real(db, active)
    finally:
        db.close()


async def _reconcile_real(db, active: list[MusicRequest]) -> None:
    """Pull live acquisition state from DroppedNeedle and apply it to our rows."""
    dn = get_droppedneedle_client()
    try:
        status_map = await dn.sync_status()
    except Exception:
        logger.exception("DroppedNeedle sync failed")
        return
    finally:
        await dn.aclose()

    for req in active:
        try:
            # APPROVED requests have not been reported yet: nudge to SEARCHING.
            info = status_map.get(req.musicbrainz_id or "")
            if info is None:
                if req.status == "APPROVED":
                    request_service.transition(db, req, "SEARCHING")
                    await event_service.emit_request_updated(
                        request_id=req.id, status=req.status, progress=req.progress,
                        owner_user_id=req.requested_by,
                    )
                continue

            new_status = info.get("status") or "SEARCHING"
            progress = info.get("progress")
            error = info.get("error")

            if new_status == req.status and (progress is None or progress == req.progress):
                continue

            if new_status == "AVAILABLE":
                request_service.sync_to_status(db, req, "AVAILABLE", progress=100)
                _sync_track_available(db, req)
                await event_service.emit_request_updated(
                    request_id=req.id, status="AVAILABLE", progress=100, owner_user_id=req.requested_by
                )
                await event_service.emit_track_updated(
                    track_id=req.track_id, status="AVAILABLE", progress=None, audience_user_ids=None
                )
            elif new_status == "FAILED":
                request_service.sync_to_status(db, req, "FAILED", error_message=error)
                await event_service.emit_request_updated(
                    request_id=req.id, status="FAILED", progress=req.progress, owner_user_id=req.requested_by
                )
            else:
                # SEARCHING / DOWNLOADING with optional progress.
                request_service.sync_to_status(db, req, new_status, progress=progress)
                if req.status == "DOWNLOADING":
                    _sync_track_downloading(db, req)
                    await event_service.emit_track_updated(
                        track_id=req.track_id, status="DOWNLOADING", progress=req.progress,
                        audience_user_ids=None,
                    )
                await event_service.emit_request_updated(
                    request_id=req.id, status=req.status, progress=req.progress,
                    owner_user_id=req.requested_by,
                )
        except Exception:
            logger.exception("Failed reconciling request %s", req.id)
            db.rollback()


async def _advance_request(db, req: MusicRequest) -> None:
    if req.status == "APPROVED":
        request_service.transition(db, req, "SEARCHING")
        await event_service.emit_request_updated(
            request_id=req.id, status=req.status, progress=req.progress, owner_user_id=req.requested_by
        )
        return

    if req.status == "SEARCHING":
        request_service.transition(db, req, "DOWNLOADING", progress=0)
        await event_service.emit_request_updated(
            request_id=req.id, status=req.status, progress=req.progress, owner_user_id=req.requested_by
        )
        _sync_track_downloading(db, req)
        await event_service.emit_track_updated(
            track_id=req.track_id, status="DOWNLOADING", progress=0, audience_user_ids=None
        )
        return

    if req.status == "DOWNLOADING":
        next_progress = min(100, (req.progress or 0) + _PROGRESS_STEP)
        if next_progress >= 100:
            request_service.transition(db, req, "AVAILABLE", progress=100)
            _sync_track_available(db, req)
            await event_service.emit_request_updated(
                request_id=req.id, status="AVAILABLE", progress=100, owner_user_id=req.requested_by
            )
            await event_service.emit_track_updated(
                track_id=req.track_id, status="AVAILABLE", progress=None, audience_user_ids=None
            )
        else:
            req.progress = next_progress
            db.commit()
            _sync_track_downloading(db, req)
            await event_service.emit_request_updated(
                request_id=req.id, status="DOWNLOADING", progress=next_progress, owner_user_id=req.requested_by
            )
            await event_service.emit_track_updated(
                track_id=req.track_id, status="DOWNLOADING", progress=next_progress, audience_user_ids=None
            )


def _sync_track_downloading(db, req: MusicRequest) -> None:
    track = db.get(Track, req.track_id)
    if track is not None:
        track.status = "DOWNLOADING"
        track.progress = req.progress
        db.commit()


def _sync_track_available(db, req: MusicRequest) -> None:
    track = db.get(Track, req.track_id)
    if track is not None:
        track.status = "AVAILABLE"
        track.available = True
        track.progress = None
        db.commit()


async def run_worker(stop_event: asyncio.Event) -> None:
    """Long-running loop; cancelled on application shutdown."""
    interval = max(1, settings.request_poll_interval_seconds)
    logger.info("Request worker started (interval=%ss)", interval)
    while not stop_event.is_set():
        try:
            await _advance_once()
        except Exception:
            logger.exception("Worker pass failed")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass
    logger.info("Request worker stopped")
