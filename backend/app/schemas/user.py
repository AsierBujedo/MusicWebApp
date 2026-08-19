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
    active: bool = True
    last_seen: Optional[datetime] = None


class CreateUserInput(CamelModel):
    username: str = Field(min_length=1, max_length=64)
    display_name: str = Field(min_length=1, max_length=120)
    email: Optional[str] = Field(default=None, max_length=255)
    role: Role = "USER"
    password: str = Field(min_length=6, max_length=256)


class UpdateUserInput(CamelModel):
    display_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    email: Optional[str] = Field(default=None, max_length=255)
    avatar: Optional[str] = Field(default=None, max_length=512)
    role: Optional[Role] = None
    active: Optional[bool] = None
