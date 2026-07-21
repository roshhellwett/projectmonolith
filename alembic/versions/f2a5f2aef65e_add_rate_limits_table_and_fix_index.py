"""add rate_limits table, drop redundant group_settings index

Revision ID: f2a5f2aef65e
Revises: f1a4f1aef64e
Create Date: 2026-07-21 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f2a5f2aef65e"
down_revision: str | Sequence[str] | None = "f1a4f1aef64e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "rate_limits" not in tables:
        op.create_table(
            "rate_limits",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.BigInteger(), nullable=False, index=True),
            sa.Column("action", sa.String(50), nullable=False),
            sa.Column("count", sa.Integer(), default=0),
            sa.Column("window_start", sa.DateTime(), nullable=False, index=True),
            sa.UniqueConstraint("user_id", "action", "window_start", name="uix_rate_limit_key"),
        )

    if "zenith_group_settings" in tables:
        existing = [i["name"] for i in inspector.get_indexes("zenith_group_settings")]
        if "ix_zenith_group_settings_chat_id" in existing:
            op.drop_index("ix_zenith_group_settings_chat_id", table_name="zenith_group_settings")


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "rate_limits" in tables:
        op.drop_table("rate_limits")

    if "zenith_group_settings" in tables:
        existing = [i["name"] for i in inspector.get_indexes("zenith_group_settings")]
        if "ix_zenith_group_settings_chat_id" not in existing:
            op.create_index("ix_zenith_group_settings_chat_id", "zenith_group_settings", ["chat_id"])
