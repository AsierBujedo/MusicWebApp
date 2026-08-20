"""Synchronise local requests with DroppedNeedle and Navidrome.

DroppedNeedle is the source of truth for acquisition. A request only becomes
available after its remote download has completed *and* Navidrome exposes a
playable song ID. Mock mode retains a deterministic simulated lifecycle.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Optional

from sqlalchemy import or_, select

from app.config import settings
from app.database import SessionLocal
from app.models.base import utcnow
from app.models.music_request import MusicRequest
from app.models.track import Track
from app.services import event_service, request_service
from app.services.integrations import get_droppedneedle_client, get_navidrome_client
from app.services.integrations.base import ExternalTrack

logger = logging.getLogger(__name__)
_MOCK_PROGRESS_STEP = 25
_SOULSEEK_RETRY_DELAY = timedelta(hours=1)
_SOULSEEK_NO_MATCH = "no matching release found on soulseek"


async def _advance_once() -> None:
    db = SessionLocal()
    try:
        await _reconcile_completed_tracks(db)
        now = utcnow()
        active = list(db.scalars(
            select(MusicRequest).where(
                or_(
                    MusicRequest.status.in_(["APPROVED", "SEARCHING", "DOWNLOADING"]),
                    (MusicRequest.status == "FAILED") & (MusicRequest.soulseek_retry_at <= now),
                )
            ).order_by(MusicRequest.created_at.asc())
        ).all())
        max_concurrent = max(1, settings.max_concurrent_download_requests)
        in_flight = sum(req.status in {"SEARCHING", "DOWNLOADING"} for req in active)
        for req in active:
            try:
                # APPROVED means queued locally. Only hand the next item to
                # DroppedNeedle once the current acquisition has reached a
                # terminal state, avoiding overlapping Soulseek searches and
                # downloads in a small homelab.
                if req.status == "APPROVED" and in_flight >= max_concurrent:
                    continue

                previous_status = req.status
                await _advance_request(db, req)
                if previous_status == "APPROVED" and req.status in {"SEARCHING", "DOWNLOADING"}:
                    in_flight += 1
                elif previous_status in {"SEARCHING", "DOWNLOADING"} and req.status not in {"SEARCHING", "DOWNLOADING"}:
                    in_flight = max(0, in_flight - 1)
                elif previous_status == "FAILED" and req.status == "APPROVED":
                    # A scheduled retry has claimed the next slot; it will be
                    # submitted on the following worker pass.
                    in_flight += 1
            except Exception:
                logger.exception("Failed advancing request %s", req.id)
                db.rollback()
    finally:
        db.close()


async def _reconcile_completed_tracks(db) -> None:
    """Repair an interrupted final state without requiring a page refresh.

    A request is transitioned to AVAILABLE only after Navidrome produced a
    playable match. Should a process restart between the track and request
    commits, the request can be terminal while the playlist copy still shows
    DOWNLOADING. Reconcile that small window on every worker pass.
    """
    stale = list(
        db.scalars(
            select(MusicRequest).where(MusicRequest.status == "AVAILABLE")
        ).all()
    )
    repaired: list[MusicRequest] = []
    for req in stale:
        track = db.get(Track, req.track_id)
        if track is None or track.status == "AVAILABLE":
            continue
        track.status = "AVAILABLE"
        track.available = True
        track.progress = None
        repaired.append(req)
    if not repaired:
        return
    db.commit()
    for req in repaired:
        await event_service.emit_track_updated(
            track_id=req.track_id, status="AVAILABLE", progress=None, audience_user_ids={req.requested_by}
        )


async def _advance_request(db, req: MusicRequest) -> None:
    if req.status == "FAILED":
        await _resume_soulseek_retry(db, req)
        return

    if settings.mock_external_services:
        await _advance_mock_request(db, req)
        return

    droppedneedle = get_droppedneedle_client()
    try:
        if req.status == "APPROVED":
            submitted = await droppedneedle.request(
                type=req.type,
                title=req.title,
                artist=req.artist,
                provider_id=req.musicbrainz_id,
            )
            if not submitted.get("accepted") or not submitted.get("external_id"):
                await _fail(db, req, str(submitted.get("reason") or "DroppedNeedle no aceptó la solicitud"))
                return
            req.external_id = str(submitted["external_id"])
            db.commit()
            await _set_request_status(db, req, "SEARCHING")
            return

        if not req.external_id:
            await _fail(db, req, "Falta el identificador remoto de la solicitud")
            return

        remote = await droppedneedle.get_status(req.external_id)
        remote_status, progress, error = _normalise_remote_status(remote)
        if remote_status == "FAILED":
            await _fail(db, req, error or "La descarga falló en DroppedNeedle")
        elif remote_status == "AVAILABLE":
            await _publish_when_indexed(db, req)
        elif remote_status in {"SEARCHING", "DOWNLOADING"}:
            await _set_request_status(db, req, remote_status, progress=progress)
    finally:
        await droppedneedle.aclose()


def _normalise_remote_status(payload: dict) -> tuple[Optional[str], Optional[int], Optional[str]]:
    """Normalise API-v1 task variants without leaking provider details."""
    source = payload.get("download", payload.get("task", payload)) if isinstance(payload, dict) else {}
    state = str(source.get("status") or source.get("state") or "").strip().lower()
    raw_progress = source.get("progress") or source.get("percent") or source.get("percentage")
    try:
        progress = max(0, min(100, int(float(raw_progress)))) if raw_progress is not None else None
    except (TypeError, ValueError):
        progress = None
    error = source.get("error") or source.get("error_message") or source.get("message")
    if state in {"failed", "error", "cancelled", "canceled", "rejected"}:
        return "FAILED", progress, str(error) if error else None
    if state in {"completed", "complete", "available", "imported", "finished"}:
        return "AVAILABLE", 100, None
    if state in {"downloading", "processing", "importing", "verifying"}:
        return "DOWNLOADING", progress, None
    if state in {"pending", "queued", "searching", "matching", "requested"}:
        return "SEARCHING", progress, None
    return None, progress, None


async def _publish_when_indexed(db, req: MusicRequest) -> None:
    """Do not expose a completed download until Navidrome can play it."""
    navidrome = get_navidrome_client()
    try:
        result = await navidrome.search(f"{req.artist} {req.title}", limit=10)
    finally:
        await navidrome.aclose()
    match = _find_navidrome_match(result.tracks, req)
    if match is None:
        # Navidrome's configured scan can lag DroppedNeedle's import. Keep the
        # request active and retry on the next worker pass instead of lying.
        await _set_request_status(db, req, "DOWNLOADING", progress=99)
        return

    track = db.get(Track, req.track_id)
    if track is None:
        await _fail(db, req, "La pista local ya no existe")
        return
    track.provider = "navidrome"
    track.provider_id = match.provider_id
    track.title = match.title
    track.artist = match.artist
    track.album = match.album
    track.album_id = match.album_id
    track.artist_id = match.artist_id
    track.year = match.year
    track.duration = match.duration
    track.cover = f"/api/covers/{track.id}" if match.cover_id else track.cover
    track.available = True
    track.status = "AVAILABLE"
    track.progress = None
    db.commit()
    # The public state machine intentionally has no SEARCHING -> AVAILABLE
    # shortcut, even when a fast remote task completes between polling passes.
    if req.status == "SEARCHING":
        await _set_request_status(db, req, "DOWNLOADING", progress=99)
    await _set_request_status(db, req, "AVAILABLE", progress=100)
    await event_service.emit_track_updated(
        track_id=track.id, status="AVAILABLE", progress=None, audience_user_ids={req.requested_by}
    )


def _find_navidrome_match(tracks: list[ExternalTrack], req: MusicRequest) -> Optional[ExternalTrack]:
    wanted_title = req.title.casefold().strip()
    wanted_artist = req.artist.casefold().strip()
    for track in tracks:
        if track.title.casefold().strip() == wanted_title and track.artist.casefold().strip() == wanted_artist:
            return track
    return tracks[0] if tracks else None


async def _set_request_status(db, req: MusicRequest, status: str, progress: Optional[int] = None) -> None:
    req = request_service.transition(db, req, status, progress=progress)
    _sync_track_downloading(db, req) if status == "DOWNLOADING" else None
    await event_service.emit_request_updated(
        request_id=req.id, status=req.status, progress=req.progress, owner_user_id=req.requested_by
    )
    if status == "DOWNLOADING":
        await event_service.emit_track_updated(
            track_id=req.track_id, status="DOWNLOADING", progress=req.progress, audience_user_ids={req.requested_by}
        )


async def _fail(db, req: MusicRequest, message: str) -> None:
    if _SOULSEEK_NO_MATCH in message.casefold():
        retry_at = utcnow() + _SOULSEEK_RETRY_DELAY
        req.soulseek_retry_count += 1
        req.soulseek_retry_at = retry_at
        req = request_service.transition(
            db,
            req,
            "FAILED",
            error_message="No matching release found on Soulseek. Se reintentará automáticamente en una hora.",
        )
        logger.info(
            "Soulseek retry scheduled for request %s at %s (attempt %s)",
            req.id,
            retry_at.isoformat(),
            req.soulseek_retry_count,
        )
        await event_service.emit_request_updated(
            request_id=req.id, status=req.status, progress=req.progress, owner_user_id=req.requested_by
        )
        return

    req = request_service.transition(db, req, "FAILED", error_message=message)
    track = db.get(Track, req.track_id)
    if track is not None:
        track.status = "REQUESTABLE"
        track.available = False
        track.progress = None
        db.commit()
    await event_service.emit_request_updated(
        request_id=req.id, status=req.status, progress=req.progress, owner_user_id=req.requested_by
    )


async def _resume_soulseek_retry(db, req: MusicRequest) -> None:
    """Turn a due retry back into a fresh DroppedNeedle submission."""
    req.external_id = None
    req.soulseek_retry_at = None
    req = request_service.transition(db, req, "APPROVED", error_message=None)
    logger.info("Resuming scheduled Soulseek retry for request %s", req.id)
    await event_service.emit_request_updated(
        request_id=req.id, status=req.status, progress=req.progress, owner_user_id=req.requested_by
    )


async def _advance_mock_request(db, req: MusicRequest) -> None:
    if req.status == "APPROVED":
        await _set_request_status(db, req, "SEARCHING")
    elif req.status == "SEARCHING":
        await _set_request_status(db, req, "DOWNLOADING", progress=0)
    elif req.status == "DOWNLOADING":
        progress = min(100, (req.progress or 0) + _MOCK_PROGRESS_STEP)
        if progress == 100:
            track = db.get(Track, req.track_id)
            if track is not None:
                track.status, track.available, track.progress = "AVAILABLE", True, None
                db.commit()
            await _set_request_status(db, req, "AVAILABLE", progress=100)
            await event_service.emit_track_updated(
                track_id=req.track_id, status="AVAILABLE", progress=None, audience_user_ids={req.requested_by}
            )
        else:
            await _set_request_status(db, req, "DOWNLOADING", progress=progress)


def _sync_track_downloading(db, req: MusicRequest) -> None:
    track = db.get(Track, req.track_id)
    if track is not None:
        track.status = "DOWNLOADING"
        track.progress = req.progress
        db.commit()


async def run_worker(stop_event: asyncio.Event) -> None:
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
