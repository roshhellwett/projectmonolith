"""drop groq_api_key column from crypto_users

Revision ID: b2b6b2cfe76e
Revises: a1d98c48e4aa
Create Date: 2026-07-21 22:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b2b6b2cfe76e"
down_revision: str | Sequence[str] | None = "a1d98c48e4aa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "crypto_users" in inspector.get_table_names():
        columns = [col["name"] for col in inspector.get_columns("crypto_users")]
        if "groq_api_key" in columns:
            op.drop_column("crypto_users", "groq_api_key")


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "crypto_users" in inspector.get_table_names():
        columns = [col["name"] for col in inspector.get_columns("crypto_users")]
        if "groq_api_key" not in columns:
            op.add_column("crypto_users", sa.Column("groq_api_key", sa.String(200), nullable=True))
