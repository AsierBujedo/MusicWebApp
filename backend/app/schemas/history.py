from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.schemas.common import CamelModel
from app.schemas.track import TrackOut


class RecordPlayInput(CamelModel):
    track_id: str = Field(min_length=1, max_length=64)


class HistoryEntryOut(CamelModel):
    track: TrackOut
    played_at: datetime
