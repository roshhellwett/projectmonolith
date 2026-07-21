"""add tokens_used to zenith_ai_usage

Revision ID: f1a4f1aef64e
Revises: e9f3e9cfe63d
Create Date: 2026-07-21 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f1a4f1aef64e"
down_revision: str | Sequence[str] | None = "e9f3e9cfe63d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "zenith_ai_usage" in inspector.get_table_names():
        columns = [col["name"] for col in inspector.get_columns("zenith_ai_usage")]
        if "tokens_used" not in columns:
            op.add_column("zenith_ai_usage", sa.Column("tokens_used", sa.Integer(), nullable=True, default=0))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "zenith_ai_usage" in inspector.get_table_names():
        columns = [col["name"] for col in inspector.get_columns("zenith_ai_usage")]
        if "tokens_used" in columns:
            op.drop_column("zenith_ai_usage", "tokens_used")
