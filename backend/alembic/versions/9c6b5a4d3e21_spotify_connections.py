"""add encrypted Spotify OAuth connections

Revision ID: 9c6b5a4d3e21
Revises: f2d8a4c7e109
Create Date: 2026-08-20
"""
from alembic import op
import sqlalchemy as sa


revision = "9c6b5a4d3e21"
down_revision = "f2d8a4c7e109"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "spotify_connections",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("user_id", sa.String(length=32), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("spotify_user_id", sa.String(length=128), nullable=False),
        sa.Column("access_token_encrypted", sa.Text(), nullable=False),
        sa.Column("refresh_token_encrypted", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", name="uq_spotify_connections_user_id"),
    )
    op.create_index("ix_spotify_connections_user_id", "spotify_connections", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_spotify_connections_user_id", table_name="spotify_connections")
    op.drop_table("spotify_connections")
