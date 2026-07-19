"""add_groq_api_key_and_raid_columns

Revision ID: c8d2c8bfd52b
Revises: b7c1b7afc41a
Create Date: 2026-07-19 16:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c8d2c8bfd52b"
down_revision: str | Sequence[str] | None = "b7c1b7afc41a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema to ensure groq_api_key and raid columns exist."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if "crypto_users" in inspector.get_table_names():
        columns = [col["name"] for col in inspector.get_columns("crypto_users")]
        if "groq_api_key" not in columns:
            op.add_column("crypto_users", sa.Column("groq_api_key", sa.String(length=200), nullable=True))

    if "zenith_group_settings" in inspector.get_table_names():
        columns = [col["name"] for col in inspector.get_columns("zenith_group_settings")]
        if "raid_mode" not in columns:
            op.add_column("zenith_group_settings", sa.Column("raid_mode", sa.Boolean(), nullable=True, default=False))
        if "raid_expires_at" not in columns:
            op.add_column("zenith_group_settings", sa.Column("raid_expires_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if "zenith_group_settings" in inspector.get_table_names():
        columns = [col["name"] for col in inspector.get_columns("zenith_group_settings")]
        if "raid_expires_at" in columns:
            op.drop_column("zenith_group_settings", "raid_expires_at")
        if "raid_mode" in columns:
            op.drop_column("zenith_group_settings", "raid_mode")

    if "crypto_users" in inspector.get_table_names():
        columns = [col["name"] for col in inspector.get_columns("crypto_users")]
        if "groq_api_key" in columns:
            op.drop_column("crypto_users", "groq_api_key")
