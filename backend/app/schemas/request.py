from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import Field

from app.schemas.common import CamelModel

RequestType = Literal["track", "album", "artist"]
RequestStatus = Literal[
    "PENDING", "APPROVED", "SEARCHING", "DOWNLOADING", "AVAILABLE", "FAILED", "REJECTED"
]


class CreateRequestInput(CamelModel):
    type: RequestType = "track"
    track_id: str = Field(min_length=1, max_length=64)


class MusicRequestOut(CamelModel):
    id: str
    type: RequestType
    track_id: str
    title: str
    artist: str
    cover: Optional[str] = None
    status: RequestStatus
    progress: Optional[int] = None
    error_message: Optional[str] = None
    soulseek_retry_count: int = 0
    soulseek_retry_at: Optional[datetime] = None
    created_at: datetime
    requested_by: Optional[str] = None
    requested_by_name: Optional[str] = None
