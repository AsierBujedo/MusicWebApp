"""Persistent rollout mode for non-administrative product features."""
from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FeatureRollout(Base):
    __tablename__ = "feature_rollouts"

    feature_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    # ``off`` | ``friends`` | ``global``. Membership is stored in
    # UserFeatureFlag, which also keeps feature checks fast for requests.
    mode: Mapped[str] = mapped_column(String(16), nullable=False, default="off")
