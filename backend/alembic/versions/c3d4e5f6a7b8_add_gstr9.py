"""add_gstr9_return_type

Revision ID: c3d4e5f6a7b8
Revises: b7e8f9a0b1c2
Create Date: 2026-05-19 00:00:00.000000

"""
from alembic import op

revision = "c3d4e5f6a7b8"
down_revision = "b7e8f9a0b1c2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE returntype ADD VALUE IF NOT EXISTS 'gstr9'")


def downgrade() -> None:
    pass  # PostgreSQL doesn't support removing enum values
