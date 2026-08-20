from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import Field

from app.schemas.common import CamelModel

Role = Literal["ADMIN", "USER"]


class UserOut(CamelModel):
    """Public user representation — never includes the password hash."""

    id: str
    username: str
    display_name: str
    email: Optional[str] = None
    avatar: Optional[str] = None
    role: Role
    auto_approve_requests: bool = False
    active: bool = True
    last_seen: Optional[datetime] = None
    feature_flags: list[str] = []


class UpdateFeatureFlagsInput(CamelModel):
    feature_flags: list[str] = Field(default_factory=list)


class CreateUserInput(CamelModel):
    username: str = Field(min_length=1, max_length=64)
    display_name: str = Field(min_length=1, max_length=120)
    email: Optional[str] = Field(default=None, max_length=255)
    role: Role = "USER"
    auto_approve_requests: bool = False
    password: str = Field(min_length=6, max_length=256)


class UpdateUserInput(CamelModel):
    display_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    email: Optional[str] = Field(default=None, max_length=255)
    avatar: Optional[str] = Field(default=None, max_length=512)
    role: Optional[Role] = None
    auto_approve_requests: Optional[bool] = None
    active: Optional[bool] = None
