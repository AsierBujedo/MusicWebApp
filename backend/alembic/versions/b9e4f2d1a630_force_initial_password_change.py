"""require a password change for provisioned accounts

Revision ID: b9e4f2d1a630
Revises: 9c6b5a4d3e21
Create Date: 2026-08-20
"""
from alembic import op
import sqlalchemy as sa


revision = "b9e4f2d1a630"
down_revision = "9c6b5a4d3e21"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    # Legacy regular accounts were provisioned before this flag existed. Make
    # their next login establish a password known only to them; bootstrap/admin
    # accounts are left alone to avoid locking the server owner out.
    op.execute("UPDATE users SET must_change_password = 1 WHERE role != 'ADMIN'")


def downgrade() -> None:
    op.drop_column("users", "must_change_password")
