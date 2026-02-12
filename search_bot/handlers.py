from sqlalchemy import select
from database.db import AsyncSessionLocal
from database.models import Notification
from pipeline.message_formatter import format_search_result

async def get_latest_results(limit=10):
    """Async fetch of recent notices."""
    async with AsyncSessionLocal() as db:
        stmt = select(Notification).order_by(Notification.published_date.desc()).limit(limit)
        result = await db.execute(stmt)
        notices = result.scalars().all()
        return format_search_result(notices)

async def search_by_keyword(query, limit=10):
    """Async case-insensitive keyword search."""
    async with AsyncSessionLocal() as db:
        stmt = select(Notification).filter(
            Notification.title.ilike(f"%{query}%")
        ).order_by(Notification.published_date.desc()).limit(limit)
        result = await db.execute(stmt)
        results = result.scalars().all()
        return format_search_result(results)