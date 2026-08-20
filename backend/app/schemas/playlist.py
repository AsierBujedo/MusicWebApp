from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import Field

from app.schemas.common import CamelModel
from app.schemas.track import TrackOut


class CreatePlaylistInput(CamelModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    shared: bool = False


class UpdatePlaylistInput(CamelModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)


class AddTrackInput(CamelModel):
    track_id: str = Field(min_length=1, max_length=64)


class ReorderInput(CamelModel):
    track_ids: List[str] = Field(default_factory=list)


class AddCollaboratorInput(CamelModel):
    username: str = Field(min_length=1, max_length=64)


class UpdateCollaboratorInput(CamelModel):
    can_reorder: bool


class PlaylistOut(CamelModel):
    id: str
    name: str
    description: Optional[str] = None
    cover: Optional[str] = None
    track_ids: List[str] = []
    tracks: Optional[List[TrackOut]] = None
    shared: bool = False
    owner_username: Optional[str] = None
    collaborator_usernames: List[str] = []
    collaborators: List[dict] = []
    created_at: datetime
