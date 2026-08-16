from __future__ import annotations

from pydantic import Field

from app.schemas.common import CamelModel


class LoginInput(CamelModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=256)


class ChangePasswordInput(CamelModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=6, max_length=256)
