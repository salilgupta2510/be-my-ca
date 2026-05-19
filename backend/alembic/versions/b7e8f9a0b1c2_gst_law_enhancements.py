"""gst_law_enhancements

Revision ID: b7e8f9a0b1c2
Revises: f66733358667
Create Date: 2026-05-19 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "b7e8f9a0b1c2"
down_revision = ("f66733358667", "a1b2c3d4e5f6")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # outward_invoices: add hsn_code
    op.add_column("outward_invoices", sa.Column("hsn_code", sa.String(8), nullable=True))

    # inward_invoices: add hsn_code, is_rcm, itc_blocked_reason
    op.add_column("inward_invoices", sa.Column("hsn_code", sa.String(8), nullable=True))
    op.add_column("inward_invoices", sa.Column("is_rcm", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("inward_invoices", sa.Column("itc_blocked_reason", sa.String(100), nullable=True))

    # businesses: add is_composition
    op.add_column("businesses", sa.Column("is_composition", sa.Boolean(), nullable=False, server_default="false"))

    # gst_returns: add gstr4 to returntype enum
    # PostgreSQL enums require ALTER TYPE
    op.execute("ALTER TYPE returntype ADD VALUE IF NOT EXISTS 'gstr4'")


def downgrade() -> None:
    op.drop_column("outward_invoices", "hsn_code")
    op.drop_column("inward_invoices", "hsn_code")
    op.drop_column("inward_invoices", "is_rcm")
    op.drop_column("inward_invoices", "itc_blocked_reason")
    op.drop_column("businesses", "is_composition")
    # PostgreSQL doesn't support removing enum values — downgrade leaves enum value in place
