"""persist DroppedNeedle request correlation identifiers

Revision ID: c74c3b7d8f10
Revises: 7de5dd9958d4
Create Date: 2026-08-19
"""
from alembic import op
import sqlalchemy as sa


revision = "c74c3b7d8f10"
down_revision = "7de5dd9958d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("music_requests", sa.Column("musicbrainz_id", sa.String(length=255), nullable=True))
    op.add_column("music_requests", sa.Column("external_id", sa.String(length=255), nullable=True))
    op.create_index("ix_music_requests_musicbrainz_id", "music_requests", ["musicbrainz_id"])
    op.create_index("ix_music_requests_external_id", "music_requests", ["external_id"])


def downgrade() -> None:
    op.drop_index("ix_music_requests_external_id", table_name="music_requests")
    op.drop_index("ix_music_requests_musicbrainz_id", table_name="music_requests")
    op.drop_column("music_requests", "external_id")
    op.drop_column("music_requests", "musicbrainz_id")
