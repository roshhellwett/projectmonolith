"""Data retention cleanup to stay within Supabase free tier (50K rows)."""

import datetime

from sqlalchemy import delete

from core.database import db_retry, get_db
from core.logger import setup_logger
from zenith_admin_bot.models import AdminAuditLog
from zenith_ai_bot.models import AIConversation, AIUsageLog
from zenith_group_bot.models import ModerationLog
from zenith_support_bot.models import SupportTicket

logger = setup_logger("DATA_CLEANUP")


@db_retry
async def run_cleanup() -> dict[str, int]:
    """Delete old rows, return dict of table -> rows_deleted."""
    results: dict[str, int] = {}

    async with get_db() as session:
        now = datetime.datetime.now(datetime.UTC)
        now_naive = now.replace(tzinfo=None)

        results["zenith_ai_conversations"] = await _do_delete(
            session, AIConversation, AIConversation.created_at,
            now_naive - datetime.timedelta(days=5),
        )

        results["zenith_moderation_log"] = await _do_delete(
            session, ModerationLog, ModerationLog.created_at,
            now_naive - datetime.timedelta(days=7),
        )

        results["admin_audit_log"] = await _do_delete(
            session, AdminAuditLog, AdminAuditLog.created_at,
            now - datetime.timedelta(days=30),
        )

        results["zenith_ai_usage"] = await _do_delete(
            session, AIUsageLog, AIUsageLog.usage_date,
            (now_naive - datetime.timedelta(days=90)).date(),
        )

        results["zenith_support_tickets"] = await _do_delete(
            session, SupportTicket, SupportTicket.created_at,
            now_naive - datetime.timedelta(days=30),
            extra_where=[SupportTicket.status.in_(["resolved", "closed"])],
        )

        await session.commit()

    total = sum(results.values())
    for table, count in results.items():
        if count > 0:
            logger.info(f"Cleaned {count} rows from {table}")
    logger.info(f"Total rows cleaned: {total}")
    return results


async def _do_delete(session, model, date_col, cutoff, extra_where=None):
    stmt = delete(model).where(date_col < cutoff)
    if extra_where:
        for clause in extra_where:
            stmt = stmt.where(clause)
    result = await session.execute(stmt)
    return result.rowcount
