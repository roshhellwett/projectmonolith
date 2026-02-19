from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from core.config import DATABASE_URL, DB_POOL_SIZE
from core.logger import setup_logger
from zenith_admin_bot.models import AdminAuditLog, BotRegistry, ActionType, BotStatus, AdminBase

logger = setup_logger("ADMIN_DB")

engine = create_async_engine(
    DATABASE_URL,
    pool_size=DB_POOL_SIZE,
    max_overflow=5,
    pool_pre_ping=True,
)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_admin_db():
    async with engine.begin() as conn:
        await conn.run_sync(AdminBase.metadata.create_all)
    logger.info("✅ Admin DB initialized")


class AdminRepo:

    @staticmethod
    async def log_action(
        admin_user_id: int,
        action: ActionType,
        target_user_id: Optional[int] = None,
        details: Optional[str] = None,
    ):
        async with AsyncSessionLocal() as session:
            log_entry = AdminAuditLog(
                admin_user_id=admin_user_id,
                action=action,
                target_user_id=target_user_id,
                details=details,
            )
            session.add(log_entry)
            await session.commit()

    @staticmethod
    async def get_audit_trail(limit: int = 20) -> list:
        async with AsyncSessionLocal() as session:
            stmt = (
                select(AdminAuditLog)
                .order_by(AdminAuditLog.created_at.desc())
                .limit(limit)
            )
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    async def get_audit_for_user(user_id: int, limit: int = 20) -> list:
        async with AsyncSessionLocal() as session:
            stmt = (
                select(AdminAuditLog)
                .where(AdminAuditLog.target_user_id == user_id)
                .order_by(AdminAuditLog.created_at.desc())
                .limit(limit)
            )
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    async def get_audit_by_action(action: ActionType, limit: int = 20) -> list:
        async with AsyncSessionLocal() as session:
            stmt = (
                select(AdminAuditLog)
                .where(AdminAuditLog.action == action)
                .order_by(AdminAuditLog.created_at.desc())
                .limit(limit)
            )
            return (await session.execute(stmt)).scalars().all()


class BotRegistryRepo:

    @staticmethod
    async def register_bot(bot_name: str, token_hash: Optional[str] = None) -> BotRegistry:
        async with AsyncSessionLocal() as session:
            stmt = select(BotRegistry).where(BotRegistry.bot_name == bot_name)
            existing = (await session.execute(stmt)).scalar_one_or_none()

            if existing:
                existing.token_hash = token_hash
                existing.status = BotStatus.ACTIVE
                existing.registered_at = datetime.now(timezone.utc)
                await session.commit()
                return existing
            else:
                new_bot = BotRegistry(
                    bot_name=bot_name,
                    token_hash=token_hash,
                    status=BotStatus.ACTIVE,
                )
                session.add(new_bot)
                await session.commit()
                await session.refresh(new_bot)
                return new_bot

    @staticmethod
    async def unregister_bot(bot_name: str):
        async with AsyncSessionLocal() as session:
            stmt = select(BotRegistry).where(BotRegistry.bot_name == bot_name)
            bot = (await session.execute(stmt)).scalar_one_or_none()
            if bot:
                bot.status = BotStatus.INACTIVE
                await session.commit()

    @staticmethod
    async def get_all_bots() -> list:
        async with AsyncSessionLocal() as session:
            stmt = select(BotRegistry).order_by(BotRegistry.registered_at.desc())
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    async def get_bot_by_name(bot_name: str) -> Optional[BotRegistry]:
        async with AsyncSessionLocal() as session:
            stmt = select(BotRegistry).where(BotRegistry.bot_name == bot_name)
            return (await session.execute(stmt)).scalar_one_or_none()

    @staticmethod
    async def update_health_status(bot_name: str, status: str):
        async with AsyncSessionLocal() as session:
            stmt = select(BotRegistry).where(BotRegistry.bot_name == bot_name)
            bot = (await session.execute(stmt)).scalar_one_or_none()
            if bot:
                bot.last_health_check = datetime.now(timezone.utc)
                bot.health_status = status
                if status == "error":
                    bot.status = BotStatus.ERROR
                await session.commit()


class MonitoringRepo:

    @staticmethod
    async def get_subscription_stats() -> dict:
        from zenith_crypto_bot.repository import SubscriptionRepo

        async with AsyncSessionLocal() as session:
            from zenith_crypto_bot.models import Subscription, CryptoUser
            from sqlalchemy import func

            total_users_res = await session.execute(select(func.count(CryptoUser.user_id)))
            total_users = total_users_res.scalar() or 0

            now = datetime.now(timezone.utc)
            pro_users_res = await session.execute(
                select(func.count(Subscription.user_id)).where(Subscription.expires_at > now)
            )
            pro_users = pro_users_res.scalar() or 0

            active_subs_res = await session.execute(
                select(func.count(Subscription.user_id)).where(Subscription.expires_at > now)
            )
            active_subs = active_subs_res.scalar() or 0

            expiring_soon_res = await session.execute(
                select(func.count(Subscription.user_id)).where(
                    Subscription.expires_at > now,
                    Subscription.expires_at <= now + timedelta(days=7)
                )
            )
            expiring_soon = expiring_soon_res.scalar() or 0

            return {
                "total_users": total_users,
                "pro_users": pro_users,
                "free_users": total_users - pro_users,
                "active_subscriptions": active_subs,
                "expiring_within_7_days": expiring_soon,
            }

    @staticmethod
    async def get_ticket_stats() -> dict:
        from zenith_support_bot.repository import TicketRepo

        try:
            return await TicketRepo.get_ticket_stats()
        except Exception as e:
            logger.error(f"Failed to get ticket stats: {e}")
            return {"total": 0, "open": 0, "in_progress": 0, "resolved": 0, "closed": 0}

    @staticmethod
    async def get_all_active_subscriptions() -> list:
        from zenith_crypto_bot.models import Subscription

        async with AsyncSessionLocal() as session:
            now = datetime.now(timezone.utc)
            stmt = (
                select(Subscription)
                .where(Subscription.expires_at > now)
                .order_by(Subscription.expires_at.asc())
            )
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    async def get_recent_keys(limit: int = 10) -> list:
        from zenith_crypto_bot.models import ActivationKey

        async with AsyncSessionLocal() as session:
            stmt = (
                select(ActivationKey)
                .where(ActivationKey.is_used == False)
                .order_by(ActivationKey.created_at.desc())
                .limit(limit)
            )
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    async def get_user_subscription_details(user_id: int) -> dict:
        from zenith_crypto_bot.models import Subscription

        async with AsyncSessionLocal() as session:
            stmt = select(Subscription).where(Subscription.user_id == user_id)
            sub = (await session.execute(stmt)).scalar_one_or_none()

            if not sub:
                return {"has_subscription": False, "days_left": 0, "expires_at": None}

            now = datetime.now(timezone.utc)
            if sub.expires_at <= now:
                return {"has_subscription": False, "days_left": 0, "expires_at": sub.expires_at}

            days_left = (sub.expires_at - now).days
            return {
                "has_subscription": True,
                "days_left": days_left,
                "expires_at": sub.expires_at,
            }

    @staticmethod
    async def get_all_tickets_admin(status: str = None, limit: int = 50, offset: int = 0) -> list:
        from zenith_support_bot.models import SupportTicket
        from sqlalchemy import desc

        async with AsyncSessionLocal() as session:
            stmt = select(SupportTicket).order_by(desc(SupportTicket.created_at))
            if status:
                stmt = stmt.where(SupportTicket.status == status)
            stmt = stmt.limit(limit).offset(offset)
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    async def get_ticket_by_id(ticket_id: int):
        from zenith_support_bot.models import SupportTicket

        async with AsyncSessionLocal() as session:
            stmt = select(SupportTicket).where(SupportTicket.id == ticket_id)
            return (await session.execute(stmt)).scalar_one_or_none()

    @staticmethod
    async def get_stale_tickets(days: int = 2) -> list:
        from zenith_support_bot.models import SupportTicket
        from utils.time_util import utc_now

        cutoff = utc_now() - timedelta(days=days)
        async with AsyncSessionLocal() as session:
            stmt = select(SupportTicket).where(
                SupportTicket.status.in_(["open", "in_progress"]),
                SupportTicket.updated_at < cutoff,
            ).order_by(SupportTicket.created_at)
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    async def get_ticket_metrics() -> dict:
        from zenith_support_bot.models import SupportTicket
        from sqlalchemy import func
        from utils.time_util import utc_now

        async with AsyncSessionLocal() as session:
            total = (await session.execute(select(func.count()).select_from(SupportTicket))).scalar() or 0
            
            open_cnt = (await session.execute(select(func.count()).select_from(SupportTicket).where(SupportTicket.status == "open"))).scalar() or 0
            in_progress = (await session.execute(select(func.count()).select_from(SupportTicket).where(SupportTicket.status == "in_progress"))).scalar() or 0
            resolved = (await session.execute(select(func.count()).select_from(SupportTicket).where(SupportTicket.status == "resolved"))).scalar() or 0
            closed = (await session.execute(select(func.count()).select_from(SupportTicket).where(SupportTicket.status == "closed"))).scalar() or 0
            
            cutoff_2d = utc_now() - timedelta(days=2)
            stale = (await session.execute(select(func.count()).select_from(SupportTicket).where(
                SupportTicket.status.in_(["open", "in_progress"]),
                SupportTicket.updated_at < cutoff_2d
            ))).scalar() or 0
            
            cutoff_7d = utc_now() - timedelta(days=7)
            resolved_7d = (await session.execute(select(func.count()).select_from(SupportTicket).where(
                SupportTicket.status == "resolved",
                SupportTicket.resolved_at >= cutoff_7d
            ))).scalar() or 0
            
            avg_rating_stmt = select(func.avg(SupportTicket.rating)).where(SupportTicket.rating.isnot(None))
            avg_rating = (await session.execute(avg_rating_stmt)).scalar() or 0
            
            return {
                "total": total,
                "open": open_cnt,
                "in_progress": in_progress,
                "resolved": resolved,
                "closed": closed,
                "stale": stale,
                "resolved_7d": resolved_7d,
                "avg_rating": round(avg_rating, 2) if avg_rating else 0,
            }

    @staticmethod
    async def search_users(query: str, limit: int = 20) -> list:
        from zenith_crypto_bot.models import CryptoUser

        async with AsyncSessionLocal() as session:
            try:
                user_id = int(query)
                stmt = select(CryptoUser).where(CryptoUser.user_id == user_id).limit(limit)
            except ValueError:
                stmt = select(CryptoUser).limit(limit)
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    async def get_all_groups(limit: int = 50, offset: int = 0) -> list:
        from zenith_group_bot.models import GroupSettings

        async with AsyncSessionLocal() as session:
            stmt = select(GroupSettings).where(GroupSettings.is_active == True).order_by(GroupSettings.chat_id.desc()).limit(limit).offset(offset)
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    async def search_groups(query: str, limit: int = 20) -> list:
        from zenith_group_bot.models import GroupSettings

        async with AsyncSessionLocal() as session:
            try:
                chat_id = int(query)
                stmt = select(GroupSettings).where(GroupSettings.chat_id == chat_id).limit(limit)
            except ValueError:
                stmt = select(GroupSettings).where(GroupSettings.group_name.ilike(f"%{query}%")).limit(limit)
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    async def get_group_count() -> int:
        from zenith_group_bot.models import GroupSettings
        from sqlalchemy import func

        async with AsyncSessionLocal() as session:
            return (await session.execute(select(func.count()).select_from(GroupSettings).where(GroupSettings.is_active == True))).scalar() or 0

    @staticmethod
    async def get_all_users(limit: int = 100, offset: int = 0) -> list:
        from zenith_crypto_bot.models import CryptoUser

        async with AsyncSessionLocal() as session:
            stmt = select(CryptoUser).order_by(CryptoUser.user_id.desc()).limit(limit).offset(offset)
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    async def get_user_count() -> int:
        from zenith_crypto_bot.models import CryptoUser
        from sqlalchemy import func

        async with AsyncSessionLocal() as session:
            return (await session.execute(select(func.count()).select_from(CryptoUser))).scalar() or 0

    @staticmethod
    async def generate_bulk_keys(count: int, days: int) -> list:
        from zenith_crypto_bot.models import ActivationKey
        import uuid

        keys = []
        async with AsyncSessionLocal() as session:
            for _ in range(count):
                key_str = f"ZENITH-{uuid.uuid4().hex[:8].upper()}-{uuid.uuid4().hex[:4].upper()}"
                key = ActivationKey(key_string=key_str, duration_days=days)
                session.add(key)
                keys.append(key_str)
            await session.commit()
        return keys

    @staticmethod
    async def get_key_usage_history(limit: int = 20) -> list:
        from zenith_crypto_bot.models import ActivationKey

        async with AsyncSessionLocal() as session:
            stmt = select(ActivationKey).where(ActivationKey.is_used == True).order_by(ActivationKey.used_at.desc()).limit(limit)
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    async def get_faq_count() -> int:
        from zenith_support_bot.models import FAQEntry
        from sqlalchemy import func

        async with AsyncSessionLocal() as session:
            return (await session.execute(select(func.count()).select_from(FAQEntry))).scalar() or 0

    @staticmethod
    async def get_canned_count() -> int:
        from zenith_support_bot.models import CannedResponse
        from sqlalchemy import func

        async with AsyncSessionLocal() as session:
            return (await session.execute(select(func.count()).select_from(CannedResponse))).scalar() or 0

    @staticmethod
    async def get_db_stats() -> dict:
        from zenith_crypto_bot.models import CryptoUser, Subscription, ActivationKey
        from zenith_support_bot.models import SupportTicket, FAQEntry, CannedResponse
        from zenith_group_bot.models import GroupSettings, ModerationLog
        from sqlalchemy import func

        async with AsyncSessionLocal() as session:
            stats = {}
            
            stats["crypto_users"] = (await session.execute(select(func.count()).select_from(CryptoUser))).scalar() or 0
            stats["subscriptions"] = (await session.execute(select(func.count()).select_from(Subscription))).scalar() or 0
            stats["activation_keys"] = (await session.execute(select(func.count()).select_from(ActivationKey))).scalar() or 0
            stats["support_tickets"] = (await session.execute(select(func.count()).select_from(SupportTicket))).scalar() or 0
            stats["faqs"] = (await session.execute(select(func.count()).select_from(FAQEntry))).scalar() or 0
            stats["canned_responses"] = (await session.execute(select(func.count()).select_from(CannedResponse))).scalar() or 0
            stats["groups"] = (await session.execute(select(func.count()).select_from(GroupSettings))).scalar() or 0
            stats["moderation_logs"] = (await session.execute(select(func.count()).select_from(ModerationLog))).scalar() or 0
            
            return stats

    @staticmethod
    async def get_revenue_report() -> dict:
        from zenith_crypto_bot.models import Subscription, ActivationKey
        from sqlalchemy import func
        from utils.time_util import utc_now

        async with AsyncSessionLocal() as session:
            now = datetime.now(timezone.utc)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            active_now = (await session.execute(select(func.count()).select_from(Subscription).where(Subscription.expires_at > now))).scalar() or 0
            
            keys_this_month = (await session.execute(select(func.count()).select_from(ActivationKey).where(
                ActivationKey.is_used == True,
                ActivationKey.used_at >= month_start
            ))).scalar() or 0
            
            total_keys_used = (await session.execute(select(func.count()).select_from(ActivationKey).where(ActivationKey.is_used == True))).scalar() or 0
            
            return {
                "active_subscriptions": active_now,
                "keys_redeemed_month": keys_this_month,
                "total_keys_redeemed": total_keys_used,
                "estimated_mrr": active_now * 149,
                "estimated_annual": active_now * 149 * 12,
            }

    @staticmethod
    async def get_all_user_ids() -> list:
        from zenith_crypto_bot.models import CryptoUser

        async with AsyncSessionLocal() as session:
            stmt = select(CryptoUser.user_id)
            return [r[0] for r in (await session.execute(stmt)).all()]

    @staticmethod
    async def get_all_pro_user_ids() -> list:
        from zenith_crypto_bot.models import Subscription
        from sqlalchemy import and_

        async with AsyncSessionLocal() as session:
            now = datetime.now(timezone.utc)
            stmt = select(Subscription.user_id).where(Subscription.expires_at > now)
            return [r[0] for r in (await session.execute(stmt)).all()]

    @staticmethod
    async def get_all_group_chat_ids() -> list:
        from zenith_group_bot.models import GroupSettings

        async with AsyncSessionLocal() as session:
            stmt = select(GroupSettings.chat_id).where(GroupSettings.is_active == True)
            return [r[0] for r in (await session.execute(stmt)).all()]


async def dispose_admin_engine():
    await engine.dispose()
