"""Persistent rate limit storage to survive restarts."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select

from core.database import get_db
from core.logger import setup_logger
from core.rate_limit_models import PersistentRateLimit

logger = setup_logger("RATE_LIMIT_REPO")


class RateLimitRepo:
    @staticmethod
    async def get_count(user_id: int, action: str, window_start: datetime) -> int:
        async with get_db() as session:
            stmt = select(PersistentRateLimit).where(
                PersistentRateLimit.user_id == user_id,
                PersistentRateLimit.action == action,
                PersistentRateLimit.window_start == window_start,
            )
            result = await session.execute(stmt)
            entry = result.scalar_one_or_none()
            return entry.count if entry else 0

    @staticmethod
    async def increment(user_id: int, action: str, window_start: datetime) -> int:
        async with get_db() as session:
            stmt = (
                select(PersistentRateLimit)
                .where(
                    PersistentRateLimit.user_id == user_id,
                    PersistentRateLimit.action == action,
                    PersistentRateLimit.window_start == window_start,
                )
                .with_for_update()
            )
            result = await session.execute(stmt)
            entry = result.scalar_one_or_none()
            if entry:
                entry.count += 1
            else:
                entry = PersistentRateLimit(
                    user_id=user_id,
                    action=action,
                    window_start=window_start,
                    count=1,
                )
                session.add(entry)
            await session.flush()
            return entry.count

    @staticmethod
    async def cleanup_old(older_than_hours: int = 24):
        cutoff = datetime.now(UTC) - timedelta(hours=older_than_hours)
        async with get_db() as session:
            stmt = delete(PersistentRateLimit).where(PersistentRateLimit.window_start < cutoff)
            result = await session.execute(stmt)
            if result.rowcount > 0:
                logger.debug(f"Cleaned up {result.rowcount} stale rate limit entries")

    @staticmethod
    async def get_all_active(action: str, since: datetime) -> dict[int, int]:
        async with get_db() as session:
            stmt = select(PersistentRateLimit).where(
                PersistentRateLimit.action == action,
                PersistentRateLimit.window_start >= since,
            )
            result = await session.execute(stmt)
            entries = result.scalars().all()
            return {e.user_id: e.count for e in entries}
