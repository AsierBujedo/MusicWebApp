"""add product feature rollout modes

Revision ID: f1a8c4d9e302
Revises: e4f7a2c9d811
Create Date: 2026-08-25
"""
from alembic import op
import sqlalchemy as sa

revision = "f1a8c4d9e302"
down_revision = "e4f7a2c9d811"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "feature_rollouts",
        sa.Column("feature_key", sa.String(length=64), primary_key=True),
        sa.Column("mode", sa.String(length=16), nullable=False, server_default="off"),
    )


def downgrade() -> None:
    op.drop_table("feature_rollouts")
