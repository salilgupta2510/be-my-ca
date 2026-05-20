"""add_itc_2b_status_to_inward_invoices

Revision ID: d1e2f3a4b5c6
Revises: c3d4e5f6a7b8
Create Date: 2026-05-20 00:00:00.000000

Section 16(2)(aa) CGST Act — ITC only claimable if invoice appears in GSTR-2B.
This column tracks per-invoice 2B reconciliation status so GSTR-3B can hard-lock
ITC to matched invoices only.
"""
from alembic import op
import sqlalchemy as sa

revision = "d1e2f3a4b5c6"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TYPE itc2bstatus AS ENUM (
            'unverified',
            'matched',
            'missing_in_2b',
            'accepted_with_risk'
        )
    """)
    op.add_column(
        "inward_invoices",
        sa.Column(
            "itc_2b_status",
            sa.Enum(
                "unverified", "matched", "missing_in_2b", "accepted_with_risk",
                name="itc2bstatus",
            ),
            nullable=False,
            server_default="unverified",
        ),
    )
    op.create_index(
        "ix_inward_invoices_itc_2b_status",
        "inward_invoices",
        ["itc_2b_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_inward_invoices_itc_2b_status", "inward_invoices")
    op.drop_column("inward_invoices", "itc_2b_status")
    op.execute("DROP TYPE itc2bstatus")
