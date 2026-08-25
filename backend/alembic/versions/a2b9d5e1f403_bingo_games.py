"""add music bingo tables

Revision ID: a2b9d5e1f403
Revises: f1a8c4d9e302
"""
from alembic import op
import sqlalchemy as sa

revision = "a2b9d5e1f403"
down_revision = "f1a8c4d9e302"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("bingo_games", sa.Column("id", sa.String(32), primary_key=True), sa.Column("host_user_id", sa.String(32), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("playlist_id", sa.String(32), sa.ForeignKey("playlists.id", ondelete="CASCADE"), nullable=False), sa.Column("join_code", sa.String(16), nullable=False, unique=True), sa.Column("title", sa.String(160), nullable=False), sa.Column("status", sa.String(16), nullable=False), sa.Column("grid_size", sa.Integer, nullable=False), sa.Column("play_seconds", sa.Integer, nullable=False), sa.Column("mark_seconds", sa.Integer, nullable=False), sa.Column("sequence_json", sa.Text, nullable=False), sa.Column("current_index", sa.Integer, nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("bingo_players", sa.Column("id", sa.String(32), primary_key=True), sa.Column("game_id", sa.String(32), sa.ForeignKey("bingo_games.id", ondelete="CASCADE"), nullable=False), sa.Column("user_id", sa.String(32), sa.ForeignKey("users.id", ondelete="SET NULL")), sa.Column("guest_token", sa.String(48), nullable=False), sa.Column("display_name", sa.String(80), nullable=False), sa.Column("card_json", sa.Text, nullable=False), sa.Column("marked_json", sa.Text, nullable=False), sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("game_id", "guest_token", name="uq_bingo_player_token"))
    op.create_table("bingo_claims", sa.Column("id", sa.String(32), primary_key=True), sa.Column("game_id", sa.String(32), sa.ForeignKey("bingo_games.id", ondelete="CASCADE"), nullable=False), sa.Column("player_id", sa.String(32), sa.ForeignKey("bingo_players.id", ondelete="CASCADE"), nullable=False), sa.Column("kind", sa.String(12), nullable=False), sa.Column("status", sa.String(12), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))

def downgrade():
    op.drop_table("bingo_claims"); op.drop_table("bingo_players"); op.drop_table("bingo_games")
