"""initial_schema

Revision ID: 95c30b455564
Revises:
Create Date: 2026-07-19 01:53:43.183480

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "95c30b455564"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
