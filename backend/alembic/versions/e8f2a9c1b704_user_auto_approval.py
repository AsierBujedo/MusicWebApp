"""allow trusted regular users to auto-approve requests

Revision ID: e8f2a9c1b704
Revises: a4b6c8d9e201
Create Date: 2026-08-19
"""
from alembic import op
import sqlalchemy as sa


revision = "e8f2a9c1b704"
down_revision = "a4b6c8d9e201"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("auto_approve_requests", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("users", "auto_approve_requests")
