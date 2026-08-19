"""schedule hourly retries when Soulseek has no matching release

Revision ID: f2d8a4c7e109
Revises: c74c3b7d8f10, e8f2a9c1b704
Create Date: 2026-08-19
"""
from alembic import op
import sqlalchemy as sa


revision = "f2d8a4c7e109"
down_revision = ("c74c3b7d8f10", "e8f2a9c1b704")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "music_requests",
        sa.Column("soulseek_retry_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("music_requests", sa.Column("soulseek_retry_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_music_requests_soulseek_retry_at", "music_requests", ["soulseek_retry_at"])


def downgrade() -> None:
    op.drop_index("ix_music_requests_soulseek_retry_at", table_name="music_requests")
    op.drop_column("music_requests", "soulseek_retry_at")
    op.drop_column("music_requests", "soulseek_retry_count")
