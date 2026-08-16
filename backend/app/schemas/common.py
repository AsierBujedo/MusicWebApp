"""Shared Pydantic base.

The frontend contract is camelCase, while Python is snake_case. We use a camel
alias generator with ``populate_by_name`` so schemas can be built from snake_case
attributes (ORM objects) but serialize to camelCase JSON.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
