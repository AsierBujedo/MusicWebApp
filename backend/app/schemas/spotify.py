from __future__ import annotations

from pydantic import Field

from app.schemas.common import CamelModel


class SpotifyStatusOut(CamelModel):
    configured: bool
    connected: bool
    display_name: str | None = None


class SpotifyPlaylistOut(CamelModel):
    id: str
    name: str
    description: str | None = None
    image: str | None = None
    track_count: int = 0
    owner_name: str | None = None


class SpotifyImportInput(CamelModel):
    playlist_ids: list[str] = Field(min_length=1, max_length=25)


class SpotifyImportOut(CamelModel):
    imported_playlists: int
    imported_tracks: int
    matched_tracks: int
    playlists: list[str] = Field(default_factory=list)
