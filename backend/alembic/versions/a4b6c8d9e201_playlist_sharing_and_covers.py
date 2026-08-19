"""add playlist collaborators and custom covers

Revision ID: a4b6c8d9e201
Revises: c74c3b7d8f10
Create Date: 2026-08-19
"""
from alembic import op
import sqlalchemy as sa

revision = "a4b6c8d9e201"
down_revision = "c74c3b7d8f10"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("playlists", sa.Column("custom_cover_path", sa.String(length=512), nullable=True))
    op.add_column("playlists", sa.Column("is_shared", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_table(
        "playlist_collaborators",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("playlist_id", sa.String(length=32), sa.ForeignKey("playlists.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(length=32), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("playlist_id", "user_id", name="uq_playlist_collaborator"),
    )
    op.create_index("ix_playlist_collaborators_playlist_id", "playlist_collaborators", ["playlist_id"])
    op.create_index("ix_playlist_collaborators_user_id", "playlist_collaborators", ["user_id"])

def downgrade() -> None:
    op.drop_index("ix_playlist_collaborators_user_id", table_name="playlist_collaborators")
    op.drop_index("ix_playlist_collaborators_playlist_id", table_name="playlist_collaborators")
    op.drop_table("playlist_collaborators")
    op.drop_column("playlists", "is_shared")
    op.drop_column("playlists", "custom_cover_path")
