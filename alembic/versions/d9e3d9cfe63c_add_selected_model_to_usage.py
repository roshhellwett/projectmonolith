"""add_selected_model_to_usage

Revision ID: d9e3d9cfe63c
Revises: c8d2c8bfd52b
Create Date: 2026-07-19 19:15:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d9e3d9cfe63c"
down_revision: str | Sequence[str] | None = "c8d2c8bfd52b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema to add selected_model to zenith_ai_usage."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if "zenith_ai_usage" in inspector.get_table_names():
        columns = [col["name"] for col in inspector.get_columns("zenith_ai_usage")]
        if "selected_model" not in columns:
            op.add_column(
                "zenith_ai_usage",
                sa.Column("selected_model", sa.String(length=50), nullable=True, default="llama-3.3-70b-versatile"),
            )


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if "zenith_ai_usage" in inspector.get_table_names():
        columns = [col["name"] for col in inspector.get_columns("zenith_ai_usage")]
        if "selected_model" in columns:
            op.drop_column("zenith_ai_usage", "selected_model")
