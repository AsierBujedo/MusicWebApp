from __future__ import annotations

from typing import Literal, Optional

from app.schemas.common import CamelModel

ServiceStatus = Literal["online", "degraded", "offline"]


class AdminStats(CamelModel):
    users: int
    requests: int
    downloads: int
    available_tracks: int


class ServiceHealth(CamelModel):
    name: str
    key: str
    status: ServiceStatus
    detail: Optional[str] = None
