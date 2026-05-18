"""add_business_invoices_returns

Revision ID: 6c640e8d78cb
Revises: eff6c52fcc5c
Create Date: 2026-05-16 14:29:35.761629

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '6c640e8d78cb'
down_revision: Union[str, None] = 'eff6c52fcc5c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'businesses',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('legal_name', sa.String(length=255), nullable=False),
        sa.Column('gstin', sa.String(length=15), nullable=False),
        sa.Column('state_code', sa.String(length=2), nullable=False),
        sa.Column('pan', sa.String(length=10), nullable=False),
        sa.Column('return_frequency', sa.Enum('monthly', 'quarterly', name='returnfrequency'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('gstin'),
        sa.UniqueConstraint('user_id'),
    )
    op.create_index(op.f('ix_businesses_user_id'), 'businesses', ['user_id'], unique=True)

    op.create_table(
        'outward_invoices',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('business_id', sa.UUID(), nullable=False),
        sa.Column('period', sa.String(length=7), nullable=False),
        sa.Column('invoice_number', sa.String(length=100), nullable=False),
        sa.Column('invoice_date', sa.Date(), nullable=False),
        sa.Column('customer_name', sa.String(length=255), nullable=False),
        sa.Column('customer_gstin', sa.String(length=15), nullable=True),
        sa.Column('place_of_supply', sa.String(length=2), nullable=False),
        sa.Column('invoice_type', sa.Enum('b2b', 'b2c_large', 'b2c_small', 'export', 'credit_note', name='invoicetype'), nullable=False),
        sa.Column('taxable_value', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('igst', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('cgst', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('sgst', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('cess', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('source', sa.Enum('manual', 'ocr_upload', 'import', name='invoicesource'), nullable=False),
        sa.Column('raw_image_url', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_outward_invoices_business_id'), 'outward_invoices', ['business_id'], unique=False)

    op.create_table(
        'inward_invoices',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('business_id', sa.UUID(), nullable=False),
        sa.Column('period', sa.String(length=7), nullable=False),
        sa.Column('supplier_name', sa.String(length=255), nullable=False),
        sa.Column('supplier_gstin', sa.String(length=15), nullable=True),
        sa.Column('invoice_number', sa.String(length=100), nullable=False),
        sa.Column('invoice_date', sa.Date(), nullable=False),
        sa.Column('taxable_value', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('igst', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('cgst', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('sgst', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_inward_invoices_business_id'), 'inward_invoices', ['business_id'], unique=False)

    op.create_table(
        'gst_returns',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('business_id', sa.UUID(), nullable=False),
        sa.Column('period', sa.String(length=7), nullable=False),
        sa.Column('return_type', sa.Enum('gstr1', 'gstr3b', name='returntype'), nullable=False),
        sa.Column('status', sa.Enum('draft', 'ready_to_file', 'filed', 'filing_failed', name='returnstatus'), nullable=False),
        sa.Column('computed_payload', sa.JSON(), nullable=False),
        sa.Column('total_tax_payable', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('itc_claimed', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('arn', sa.String(length=50), nullable=True),
        sa.Column('filed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_gst_returns_business_id'), 'gst_returns', ['business_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_gst_returns_business_id'), table_name='gst_returns')
    op.drop_table('gst_returns')
    op.drop_index(op.f('ix_inward_invoices_business_id'), table_name='inward_invoices')
    op.drop_table('inward_invoices')
    op.drop_index(op.f('ix_outward_invoices_business_id'), table_name='outward_invoices')
    op.drop_table('outward_invoices')
    op.drop_index(op.f('ix_businesses_user_id'), table_name='businesses')
    op.drop_table('businesses')
    op.execute("DROP TYPE IF EXISTS returnfrequency")
    op.execute("DROP TYPE IF EXISTS invoicetype")
    op.execute("DROP TYPE IF EXISTS invoicesource")
    op.execute("DROP TYPE IF EXISTS returntype")
    op.execute("DROP TYPE IF EXISTS returnstatus")
