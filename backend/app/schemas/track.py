from __future__ import annotations

from typing import List, Literal, Optional

from app.schemas.common import CamelModel

TrackStatus = Literal["AVAILABLE", "REQUESTABLE", "PENDING", "DOWNLOADING", "UNAVAILABLE"]


class TrackOut(CamelModel):
    id: str
    title: str
    artist: str
    artist_id: Optional[str] = None
    album: Optional[str] = None
    album_id: Optional[str] = None
    cover: Optional[str] = None
    year: Optional[int] = None
    duration: Optional[int] = None
    status: TrackStatus
    requestable: Optional[bool] = None
    progress: Optional[int] = None


class AlbumOut(CamelModel):
    id: str
    title: str
    artist: str
    artist_id: Optional[str] = None
    cover: Optional[str] = None
    year: Optional[int] = None
    track_count: Optional[int] = None
    status: TrackStatus


class ArtistOut(CamelModel):
    id: str
    name: str
    image: Optional[str] = None
    album_count: Optional[int] = None


class SearchResults(CamelModel):
    tracks: List[TrackOut] = []
    albums: List[AlbumOut] = []
    artists: List[ArtistOut] = []
