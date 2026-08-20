"""add per-user admin feature flags

Revision ID: d2f8c1a9b305
Revises: c1e9a4b7d203
Create Date: 2026-08-20
"""
from alembic import op
import sqlalchemy as sa
revision = "d2f8c1a9b305"
down_revision = "c1e9a4b7d203"
branch_labels = None
depends_on = None
def upgrade():
    op.create_table("user_feature_flags", sa.Column("id", sa.String(32), primary_key=True), sa.Column("user_id", sa.String(32), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("feature_key", sa.String(64), nullable=False), sa.UniqueConstraint("user_id", "feature_key", name="uq_user_feature_flag"))
    op.create_index("ix_user_feature_flags_user_id", "user_feature_flags", ["user_id"])
def downgrade():
    op.drop_index("ix_user_feature_flags_user_id", table_name="user_feature_flags")
    op.drop_table("user_feature_flags")
