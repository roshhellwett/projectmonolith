from datetime import date

from sqlalchemy import delete, func, select

from core.database import AsyncSessionLocal, db_retry
from core.logger import setup_logger
from zenith_ai_bot.models import AIConversation, AIUsageLog

logger = setup_logger("AI_REPO")


class ConversationRepo:
    @staticmethod
    @db_retry
    async def add_message(user_id: int, role: str, content: str):
        async with AsyncSessionLocal() as session:
            session.add(AIConversation(user_id=user_id, role=role, content=content[:2000]))
            await session.commit()

    @staticmethod
    @db_retry
    async def get_history(user_id: int, limit: int = 10) -> list:
        async with AsyncSessionLocal() as session:
            stmt = (
                select(AIConversation)
                .where(AIConversation.user_id == user_id)
                .order_by(AIConversation.created_at.desc())
                .limit(limit)
            )
            rows = (await session.execute(stmt)).scalars().all()
            return list(reversed(rows))

    @staticmethod
    @db_retry
    async def clear_history(user_id: int) -> int:
        async with AsyncSessionLocal() as session:
            stmt = delete(AIConversation).where(AIConversation.user_id == user_id)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount

    @staticmethod
    @db_retry
    async def count_messages(user_id: int) -> int:
        async with AsyncSessionLocal() as session:
            stmt = select(func.count()).select_from(AIConversation).where(AIConversation.user_id == user_id)
            return (await session.execute(stmt)).scalar() or 0


class UsageRepo:
    @staticmethod
    @db_retry
    async def _get_or_create(session, user_id: int) -> AIUsageLog:
        today = date.today()
        stmt = select(AIUsageLog).where(AIUsageLog.user_id == user_id, AIUsageLog.usage_date == today)
        row = (await session.execute(stmt)).scalar_one_or_none()
        if not row:
            last_stmt = select(AIUsageLog).where(AIUsageLog.user_id == user_id).order_by(AIUsageLog.usage_date.desc()).limit(1)
            last_row = (await session.execute(last_stmt)).scalar_one_or_none()
            default_persona = last_row.persona if last_row and last_row.persona else "default"
            default_model = last_row.selected_model if last_row and last_row.selected_model else "llama-3.3-70b-versatile"

            row = AIUsageLog(
                user_id=user_id,
                usage_date=today,
                query_count=0,
                summarize_count=0,
                persona=default_persona,
                selected_model=default_model,
            )
            session.add(row)
            await session.flush()
        return row

    @staticmethod
    @db_retry
    async def increment_queries(user_id: int) -> int:
        async with AsyncSessionLocal() as session:
            row = await UsageRepo._get_or_create(session, user_id)
            row.query_count += 1
            await session.commit()
            return row.query_count

    @staticmethod
    @db_retry
    async def increment_summarize(user_id: int) -> int:
        async with AsyncSessionLocal() as session:
            row = await UsageRepo._get_or_create(session, user_id)
            row.summarize_count += 1
            await session.commit()
            return row.summarize_count

    @staticmethod
    @db_retry
    async def get_today_usage(user_id: int) -> dict:
        async with AsyncSessionLocal() as session:
            row = await UsageRepo._get_or_create(session, user_id)
            return {
                "queries": row.query_count,
                "summarizes": row.summarize_count,
                "persona": row.persona or "default",
                "selected_model": row.selected_model or "llama-3.3-70b-versatile",
            }

    @staticmethod
    @db_retry
    async def set_persona(user_id: int, persona: str):
        async with AsyncSessionLocal() as session:
            row = await UsageRepo._get_or_create(session, user_id)
            row.persona = persona
            await session.commit()

    @staticmethod
    @db_retry
    async def get_persona(user_id: int) -> str:
        async with AsyncSessionLocal() as session:
            row = await UsageRepo._get_or_create(session, user_id)
            return row.persona or "default"

    @staticmethod
    @db_retry
    async def set_selected_model(user_id: int, model_id: str):
        async with AsyncSessionLocal() as session:
            row = await UsageRepo._get_or_create(session, user_id)
            row.selected_model = model_id
            await session.commit()

    @staticmethod
    @db_retry
    async def get_selected_model(user_id: int) -> str:
        async with AsyncSessionLocal() as session:
            row = await UsageRepo._get_or_create(session, user_id)
            return row.selected_model or "llama-3.3-70b-versatile"
