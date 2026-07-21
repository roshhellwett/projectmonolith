"""add composite indexes for query performance

Revision ID: e9f3e9cfe63d
Revises: d9e3d9cfe63c
Create Date: 2026-07-21 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e9f3e9cfe63d"
down_revision: str | Sequence[str] | None = "d9e3d9cfe63c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # --- crypto_subscriptions ---
    if "crypto_subscriptions" in tables:
        existing = [i["name"] for i in inspector.get_indexes("crypto_subscriptions")]
        if "ix_crypto_subscriptions_expires_at" not in existing:
            op.create_index("ix_crypto_subscriptions_expires_at", "crypto_subscriptions", ["expires_at", "user_id"])

    # --- zenith_ai_conversations ---
    if "zenith_ai_conversations" in tables:
        existing = [i["name"] for i in inspector.get_indexes("zenith_ai_conversations")]
        if "ix_zenith_ai_conversations_user_date" not in existing:
            op.create_index(
                "ix_zenith_ai_conversations_user_date",
                "zenith_ai_conversations",
                ["user_id", sa.text("created_at DESC")],
                postgresql_using="btree",
            )

    # --- zenith_ai_usage ---
    if "zenith_ai_usage" in tables:
        existing = [i["name"] for i in inspector.get_indexes("zenith_ai_usage")]
        if "ix_zenith_ai_usage_user_date" not in existing:
            op.create_index("ix_zenith_ai_usage_user_date", "zenith_ai_usage", ["user_id", "usage_date"])

    # --- crypto_price_alerts ---
    if "crypto_price_alerts" in tables:
        existing = [i["name"] for i in inspector.get_indexes("crypto_price_alerts")]
        if "ix_crypto_price_alerts_active" not in existing:
            op.create_index("ix_crypto_price_alerts_active", "crypto_price_alerts", ["is_triggered", "token_id"])

    # --- zenith_support_tickets ---
    if "zenith_support_tickets" in tables:
        existing = [i["name"] for i in inspector.get_indexes("zenith_support_tickets")]
        if "ix_zenith_support_tickets_user_status" not in existing:
            op.create_index("ix_zenith_support_tickets_user_status", "zenith_support_tickets", ["user_id", "status"])
        if "ix_tickets_created_at" not in existing:
            op.create_index("ix_tickets_created_at", "zenith_support_tickets", [sa.text("created_at DESC")])

    # --- zenith_moderation_log ---
    if "zenith_moderation_log" in tables:
        existing = [i["name"] for i in inspector.get_indexes("zenith_moderation_log")]
        if "ix_zenith_moderation_log_chat_date" not in existing:
            op.create_index(
                "ix_zenith_moderation_log_chat_date",
                "zenith_moderation_log",
                ["chat_id", sa.text("created_at DESC")],
            )

    # --- zenith_group_settings ---
    if "zenith_group_settings" in tables:
        existing = [i["name"] for i in inspector.get_indexes("zenith_group_settings")]
        if "ix_zenith_group_settings_owner" not in existing:
            op.create_index("ix_zenith_group_settings_owner", "zenith_group_settings", ["owner_id"])

    # --- admin_audit_log ---
    if "admin_audit_log" in tables:
        existing = [i["name"] for i in inspector.get_indexes("admin_audit_log")]
        if "ix_admin_audit_log_admin_date" not in existing:
            op.create_index(
                "ix_admin_audit_log_admin_date", "admin_audit_log", ["admin_user_id", sa.text("created_at DESC")]
            )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    index_map = {
        "crypto_subscriptions": ["ix_crypto_subscriptions_expires_at"],
        "zenith_ai_conversations": ["ix_zenith_ai_conversations_user_date"],
        "zenith_ai_usage": ["ix_zenith_ai_usage_user_date"],
        "crypto_price_alerts": ["ix_crypto_price_alerts_active"],
        "zenith_support_tickets": ["ix_zenith_support_tickets_user_status", "ix_tickets_created_at"],
        "zenith_moderation_log": ["ix_zenith_moderation_log_chat_date"],
        "zenith_group_settings": ["ix_zenith_group_settings_owner"],
        "admin_audit_log": ["ix_admin_audit_log_admin_date"],
    }

    for table_name, indexes in index_map.items():
        if table_name in tables:
            existing = [i["name"] for i in inspector.get_indexes(table_name)]
            for idx_name in indexes:
                if idx_name in existing:
                    op.drop_index(idx_name, table_name=table_name)
