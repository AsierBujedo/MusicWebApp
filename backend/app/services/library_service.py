"""Track/library helpers: persisting external metadata behind stable backend
IDs and converting ORM tracks into the frontend ``Track`` shape."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.models.base import utcnow
from app.models.track import Track
from app.schemas.track import TrackOut
from app.services.integrations.base import ExternalTrack

# Statuses in which a track can be (re)requested by a user.
REQUESTABLE_STATUSES = {"REQUESTABLE", "UNAVAILABLE"}
ACTIVE_REQUEST_STATUSES = {"PENDING", "DOWNLOADING"}


def _status_for(external: ExternalTrack) -> str:
    return external.status or ("AVAILABLE" if external.available else "REQUESTABLE")


def upsert_external_track(db: DbSession, external: ExternalTrack) -> Track:
    """Find or create a local Track for an external result, keeping metadata
    fresh. Never downgrades a track that is mid-request (PENDING/DOWNLOADING)."""
    track = db.scalar(
        select(Track).where(
            Track.provider == external.provider, Track.provider_id == external.provider_id
        )
    )
    if track is None:
        track = Track(
            provider=external.provider,
            provider_id=external.provider_id,
            title=external.title,
            artist=external.artist,
            artist_id=external.artist_id,
            album=external.album,
            album_id=external.album_id,
            cover=external.cover,
            year=external.year,
            duration=external.duration,
            available=external.available,
            status=_status_for(external),
        )
        db.add(track)
        db.commit()
        db.refresh(track)
        if external.cover_id:
            track.cover = f"/api/covers/{track.id}"
            db.commit()
            db.refresh(track)
        return track

    # Refresh metadata.
    track.title = external.title
    track.artist = external.artist
    track.artist_id = external.artist_id
    track.album = external.album
    track.album_id = external.album_id
    track.cover = f"/api/covers/{track.id}" if external.cover_id else external.cover or track.cover
    track.year = external.year
    track.duration = external.duration
    track.updated_at = utcnow()

    # Only touch availability/status when not in an active request lifecycle.
    if track.status not in ACTIVE_REQUEST_STATUSES:
        track.available = external.available
        track.status = _status_for(external)
    db.commit()
    db.refresh(track)
    return track


def get_track(db: DbSession, track_id: str) -> Optional[Track]:
    return db.get(Track, track_id)


def to_out(track: Track) -> TrackOut:
    return TrackOut(
        id=track.id,
        title=track.title,
        artist=track.artist,
        artist_id=track.artist_id,
        album=track.album,
        album_id=track.album_id,
        cover=track.cover,
        year=track.year,
        duration=track.duration,
        status=track.status,  # type: ignore[arg-type]
        requestable=track.status in REQUESTABLE_STATUSES,
        progress=track.progress if track.status == "DOWNLOADING" else None,
    )
