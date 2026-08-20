"""add playlist collaborator reorder permission

Revision ID: c1e9a4b7d203
Revises: b9e4f2d1a630
Create Date: 2026-08-20
"""
from alembic import op
import sqlalchemy as sa


revision = "c1e9a4b7d203"
down_revision = "b9e4f2d1a630"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "playlist_collaborators",
        sa.Column("can_reorder", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("playlist_collaborators", "can_reorder")
