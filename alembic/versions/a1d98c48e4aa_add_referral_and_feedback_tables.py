"""add_referral_and_feedback_tables

Revision ID: a1d98c48e4aa
Revises: f2a5f2aef65e
Create Date: 2026-07-21 21:33:41.603543

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1d98c48e4aa'
down_revision: Union[str, Sequence[str], None] = 'f2a5f2aef65e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('referral_codes',
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('code', sa.String(length=20), nullable=False),
    sa.Column('total_redeemed', sa.Integer(), nullable=True),
    sa.Column('bonus_days', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('user_id')
    )
    op.create_index(op.f('ix_referral_codes_code'), 'referral_codes', ['code'], unique=True)
    op.create_table('referral_redemptions',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('referrer_id', sa.BigInteger(), nullable=False),
    sa.Column('redeemed_by', sa.BigInteger(), nullable=False),
    sa.Column('redeemed_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('redeemed_by')
    )
    op.create_index(op.f('ix_referral_redemptions_referrer_id'), 'referral_redemptions', ['referrer_id'], unique=False)
    op.create_table('user_feedback',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('message', sa.String(length=2000), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_feedback_user_id'), 'user_feedback', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_user_feedback_user_id'), table_name='user_feedback')
    op.drop_table('user_feedback')
    op.drop_index(op.f('ix_referral_redemptions_referrer_id'), table_name='referral_redemptions')
    op.drop_table('referral_redemptions')
    op.drop_index(op.f('ix_referral_codes_code'), table_name='referral_codes')
    op.drop_table('referral_codes')
