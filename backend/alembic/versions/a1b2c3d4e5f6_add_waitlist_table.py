"""add_waitlist_table

Revision ID: a1b2c3d4e5f6
Revises: f66733358667
Create Date: 2026-05-19 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f66733358667'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'waitlist',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_waitlist_email'), 'waitlist', ['email'], unique=True)
    op.create_index(op.f('ix_waitlist_id'), 'waitlist', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_waitlist_email'), table_name='waitlist')
    op.drop_index(op.f('ix_waitlist_id'), table_name='waitlist')
    op.drop_table('waitlist')
