"""add persistent download maintenance switch

Revision ID: e4f7a2c9d811
Revises: d2f8c1a9b305
Create Date: 2026-08-25
"""
from alembic import op
import sqlalchemy as sa

revision = "e4f7a2c9d811"
down_revision = "d2f8c1a9b305"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(length=64), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_table("system_settings")
