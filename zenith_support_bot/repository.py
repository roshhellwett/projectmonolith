import asyncio
import functools
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, delete, update, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from cachetools import TTLCache

from zenith_support_bot.models import Base, SupportTicket, FAQEntry, CannedResponse
from core.config import DATABASE_URL, DB_POOL_SIZE
from utils.time_util import utc_now
from core.logger import setup_logger

logger = setup_logger("SUPPORT_DB")

engine = create_async_engine(DATABASE_URL, pool_size=DB_POOL_SIZE, max_overflow=5, pool_pre_ping=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

ticket_cache = TTLCache(maxsize=1000, ttl=300)
faq_cache = TTLCache(maxsize=500, ttl=300)


async def init_support_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_default_faq()
    logger.info("✅ Support DB initialized")


async def dispose_support_engine():
    await engine.dispose()


def db_retry(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        for attempt in range(3):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if attempt == 2:
                    raise
                logger.warning(f"DB Network Blip in {func.__name__}, retrying... ({e})")
                await asyncio.sleep(0.5 * (2 ** attempt))
    return wrapper


async def seed_default_faq():
    default_faqs = [
        {"question": "How do I upgrade to Pro?", "answer": "Use /activate [KEY] with your activation key to upgrade to Pro. Pro users enjoy unlimited tickets, AI auto-responses, priority support, and more.", "category": "billing"},
        {"question": "How do I create a ticket?", "answer": "Use /ticket [subject] | [description]. For example: /ticket Login Issue | I can't log into my account.", "category": "tickets"},
        {"question": "How do I check my ticket status?", "answer": "Use /status [TICKET_ID] to check the status of your ticket. You can also use /mytickets to see all your open tickets.", "category": "tickets"},
        {"question": "How do I close a ticket?", "answer": "Use /close [TICKET_ID] to close your own ticket. Only open tickets can be closed.", "category": "tickets"},
        {"question": "What are the ticket priorities?", "answer": "Pro users can set priorities: Low, Normal, High, Urgent. Higher priority tickets are addressed faster by our team.", "category": "tickets"},
    ]
    async with AsyncSessionLocal() as session:
        for faq_data in default_faqs:
            stmt = pg_insert(FAQEntry).values(
                question=faq_data["question"],
                answer=faq_data["answer"],
                category=faq_data["category"],
                created_by=None,
            ).on_conflict_do_nothing()
            await session.execute(stmt)
        await session.commit()
    faq_cache.clear()


class TicketRepo:
    @staticmethod
    @db_retry
    async def create_ticket(user_id: int, username: str, subject: str, description: str) -> SupportTicket:
        async with AsyncSessionLocal() as session:
            ticket = SupportTicket(
                user_id=user_id,
                username=username,
                subject=subject,
                description=description,
                status="open",
                priority="normal",
            )
            session.add(ticket)
            await session.commit()
            await session.refresh(ticket)
            return ticket

    @staticmethod
    @db_retry
    async def get_ticket(ticket_id: int) -> SupportTicket:
        cache_key = f"ticket_{ticket_id}"
        if cache_key in ticket_cache:
            return ticket_cache[cache_key]
        async with AsyncSessionLocal() as session:
            stmt = select(SupportTicket).where(SupportTicket.id == ticket_id)
            ticket = (await session.execute(stmt)).scalar_one_or_none()
            if ticket:
                ticket_cache[cache_key] = ticket
            return ticket

    @staticmethod
    @db_retry
    async def get_user_tickets(user_id: int, open_only: bool = True) -> list:
        async with AsyncSessionLocal() as session:
            stmt = select(SupportTicket).where(SupportTicket.user_id == user_id)
            if open_only:
                stmt = stmt.where(SupportTicket.status.in_(["open", "in_progress"]))
            stmt = stmt.order_by(SupportTicket.created_at.desc())
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    @db_retry
    async def count_open_tickets(user_id: int) -> int:
        async with AsyncSessionLocal() as session:
            stmt = select(func.count()).select_from(SupportTicket).where(
                SupportTicket.user_id == user_id,
                SupportTicket.status.in_(["open", "in_progress"]),
            )
            return (await session.execute(stmt)).scalar() or 0

    @staticmethod
    @db_retry
    async def update_ticket_status(ticket_id: int, status: str) -> bool:
        async with AsyncSessionLocal() as session:
            stmt = update(SupportTicket).where(SupportTicket.id == ticket_id).values(
                status=status,
                updated_at=utc_now(),
                resolved_at=utc_now() if status == "resolved" else None,
            )
            result = await session.execute(stmt)
            await session.commit()
            ticket_cache.pop(f"ticket_{ticket_id}", None)
            return result.rowcount > 0

    @staticmethod
    @db_retry
    async def set_priority(ticket_id: int, priority: str) -> bool:
        async with AsyncSessionLocal() as session:
            stmt = update(SupportTicket).where(SupportTicket.id == ticket_id).values(
                priority=priority,
                updated_at=utc_now(),
            )
            result = await session.execute(stmt)
            await session.commit()
            ticket_cache.pop(f"ticket_{ticket_id}", None)
            return result.rowcount > 0

    @staticmethod
    @db_retry
    async def set_ai_response(ticket_id: int, ai_response: str) -> bool:
        async with AsyncSessionLocal() as session:
            stmt = update(SupportTicket).where(SupportTicket.id == ticket_id).values(
                ai_response=ai_response,
                status="in_progress",
                updated_at=utc_now(),
            )
            result = await session.execute(stmt)
            await session.commit()
            ticket_cache.pop(f"ticket_{ticket_id}", None)
            return result.rowcount > 0

    @staticmethod
    @db_retry
    async def set_admin_response(ticket_id: int, admin_response: str) -> bool:
        async with AsyncSessionLocal() as session:
            stmt = update(SupportTicket).where(SupportTicket.id == ticket_id).values(
                admin_response=admin_response,
                status="resolved",
                updated_at=utc_now(),
                resolved_at=utc_now(),
            )
            result = await session.execute(stmt)
            await session.commit()
            ticket_cache.pop(f"ticket_{ticket_id}", None)
            return result.rowcount > 0

    @staticmethod
    @db_retry
    async def set_rating(ticket_id: int, rating: int) -> bool:
        async with AsyncSessionLocal() as session:
            stmt = update(SupportTicket).where(SupportTicket.id == ticket_id).values(
                rating=rating,
                updated_at=utc_now(),
            )
            result = await session.execute(stmt)
            await session.commit()
            ticket_cache.pop(f"ticket_{ticket_id}", None)
            return result.rowcount > 0

    @staticmethod
    @db_retry
    async def close_ticket(ticket_id: int, user_id: int) -> bool:
        async with AsyncSessionLocal() as session:
            stmt = update(SupportTicket).where(
                SupportTicket.id == ticket_id,
                SupportTicket.user_id == user_id,
                SupportTicket.status.in_(["open", "in_progress"]),
            ).values(
                status="closed",
                updated_at=utc_now(),
            )
            result = await session.execute(stmt)
            await session.commit()
            ticket_cache.pop(f"ticket_{ticket_id}", None)
            return result.rowcount > 0

    @staticmethod
    @db_retry
    async def get_stale_tickets(days: int = 7) -> list:
        async with AsyncSessionLocal() as session:
            cutoff = utc_now() - timedelta(days=days)
            stmt = select(SupportTicket).where(
                SupportTicket.status.in_(["open", "in_progress"]),
                SupportTicket.updated_at < cutoff,
            )
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    @db_retry
    async def get_all_tickets(limit: int = 50, offset: int = 0) -> list:
        async with AsyncSessionLocal() as session:
            stmt = select(SupportTicket).order_by(SupportTicket.created_at.desc()).limit(limit).offset(offset)
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    @db_retry
    async def get_ticket_stats() -> dict:
        async with AsyncSessionLocal() as session:
            total = (await session.execute(select(func.count()).select_from(SupportTicket))).scalar() or 0
            open_cnt = (await session.execute(select(func.count()).select_from(SupportTicket).where(SupportTicket.status == "open"))).scalar() or 0
            in_progress = (await session.execute(select(func.count()).select_from(SupportTicket).where(SupportTicket.status == "in_progress"))).scalar() or 0
            resolved = (await session.execute(select(func.count()).select_from(SupportTicket).where(SupportTicket.status == "resolved"))).scalar() or 0
            closed = (await session.execute(select(func.count()).select_from(SupportTicket).where(SupportTicket.status == "closed"))).scalar() or 0
            
            avg_rating_stmt = select(func.avg(SupportTicket.rating)).where(SupportTicket.rating.isnot(None))
            avg_rating = (await session.execute(avg_rating_stmt)).scalar() or 0
            
            return {
                "total": total,
                "open": open_cnt,
                "in_progress": in_progress,
                "resolved": resolved,
                "closed": closed,
                "avg_rating": round(avg_rating, 2) if avg_rating else 0,
            }


class FAQRepo:
    @staticmethod
    @db_retry
    async def add_faq(question: str, answer: str, category: str, created_by: int) -> FAQEntry:
        async with AsyncSessionLocal() as session:
            faq = FAQEntry(
                question=question,
                answer=answer,
                category=category,
                created_by=created_by,
            )
            session.add(faq)
            await session.commit()
            await session.refresh(faq)
            faq_cache.clear()
            return faq

    @staticmethod
    @db_retry
    async def delete_faq(faq_id: int) -> bool:
        async with AsyncSessionLocal() as session:
            stmt = delete(FAQEntry).where(FAQEntry.id == faq_id)
            result = await session.execute(stmt)
            await session.commit()
            faq_cache.clear()
            return result.rowcount > 0

    @staticmethod
    @db_retry
    async def get_faq(faq_id: int) -> FAQEntry:
        if faq_id in faq_cache:
            return faq_cache[faq_id]
        async with AsyncSessionLocal() as session:
            stmt = select(FAQEntry).where(FAQEntry.id == faq_id)
            faq = (await session.execute(stmt)).scalar_one_or_none()
            if faq:
                faq_cache[faq_id] = faq
            return faq

    @staticmethod
    @db_retry
    async def get_all_faqs(limit: int = 100) -> list:
        async with AsyncSessionLocal() as session:
            stmt = select(FAQEntry).order_by(FAQEntry.created_at.desc()).limit(limit)
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    @db_retry
    async def get_faqs_by_category(category: str) -> list:
        async with AsyncSessionLocal() as session:
            stmt = select(FAQEntry).where(FAQEntry.category == category).order_by(FAQEntry.created_at.desc())
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    @db_retry
    async def search_faqs(query: str) -> list:
        async with AsyncSessionLocal() as session:
            stmt = select(FAQEntry).where(
                (FAQEntry.question.ilike(f"%{query}%")) | (FAQEntry.answer.ilike(f"%{query}%"))
            ).limit(10)
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    @db_retry
    async def count_faqs() -> int:
        async with AsyncSessionLocal() as session:
            return (await session.execute(select(func.count()).select_from(FAQEntry))).scalar() or 0


class CannedRepo:
    @staticmethod
    @db_retry
    async def add_canned(tag: str, content: str, created_by: int) -> CannedResponse:
        async with AsyncSessionLocal() as session:
            canned = CannedResponse(
                tag=tag,
                content=content,
                created_by=created_by,
            )
            session.add(canned)
            await session.commit()
            await session.refresh(canned)
            return canned

    @staticmethod
    @db_retry
    async def get_canned(tag: str) -> CannedResponse:
        async with AsyncSessionLocal() as session:
            stmt = select(CannedResponse).where(CannedResponse.tag == tag)
            return (await session.execute(stmt)).scalar_one_or_none()

    @staticmethod
    @db_retry
    async def get_all_canned() -> list:
        async with AsyncSessionLocal() as session:
            stmt = select(CannedResponse).order_by(CannedResponse.usage_count.desc())
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    @db_retry
    async def increment_usage(tag: str) -> bool:
        async with AsyncSessionLocal() as session:
            stmt = update(CannedResponse).where(CannedResponse.tag == tag).values(
                usage_count=CannedResponse.usage_count + 1
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    @staticmethod
    @db_retry
    async def delete_canned(tag: str) -> bool:
        async with AsyncSessionLocal() as session:
            stmt = delete(CannedResponse).where(CannedResponse.tag == tag)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    @staticmethod
    @db_retry
    async def count_canned() -> int:
        async with AsyncSessionLocal() as session:
            return (await session.execute(select(func.count()).select_from(CannedResponse))).scalar() or 0
