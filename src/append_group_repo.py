import sys

repo_code = '''
from zenith_group_bot.models import GroupSubscription, GroupActivationKey
import uuid
from datetime import UTC, datetime, timedelta
from sqlalchemy import select
from core.database import AsyncSessionLocal, db_retry
from core.permissions import invalidate_tier_cache

class GroupSubscriptionRepo:
    @staticmethod
    @db_retry
    async def generate_key(days: int, validity_days: int = 365) -> str:
        new_key = f"ZENITH-GRP-{uuid.uuid4().hex[:8].upper()}-{uuid.uuid4().hex[:4].upper()}"
        async with AsyncSessionLocal() as session:
            expires_at = datetime.now(UTC) + timedelta(days=validity_days)
            session.add(GroupActivationKey(key_string=new_key, duration_days=days, expires_at=expires_at))
            await session.commit()
        return new_key

    @staticmethod
    @db_retry
    async def redeem_key(user_id: int, key_string: str) -> tuple[bool, str]:
        async with AsyncSessionLocal() as session, session.begin():
            res = await session.execute(
                select(GroupActivationKey).where(GroupActivationKey.key_string == key_string).with_for_update()
            )
            key = res.scalar_one_or_none()
            if not key or key.is_used:
                return False, "❌ <b>Activation Failed:</b> Invalid or already used key."

            if key.expires_at and key.expires_at <= datetime.now(UTC):
                return False, "❌ <b>Activation Failed:</b> This key has expired."

            key.is_used = True
            key.used_by = user_id
            key.used_at = datetime.now(UTC)

            res = await session.execute(select(GroupSubscription).where(GroupSubscription.user_id == user_id).with_for_update())
            sub = res.scalar_one_or_none()
            now = datetime.now(UTC)
            add_on = timedelta(days=key.duration_days)
            if sub and sub.expires_at > now:
                sub.expires_at += add_on
            else:
                new_expiry = now + add_on
                if sub:
                    sub.expires_at = new_expiry
                else:
                    session.add(GroupSubscription(user_id=user_id, expires_at=new_expiry))
            invalidate_tier_cache(user_id)
            return True, (
                f"💎 <b>ZENITH PRO ACTIVATED (GROUP)</b>\\n\\n"
                f"✅ Successfully applied <b>{key.duration_days} days</b> to your account.\\n"
                f"Enjoy Group features."
            )

    @staticmethod
    @db_retry
    async def get_days_left(user_id: int) -> int:
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(GroupSubscription).where(GroupSubscription.user_id == user_id))
            sub = res.scalar_one_or_none()
            now = datetime.now(UTC)
            if not sub or sub.expires_at <= now:
                return 0
            remaining = sub.expires_at - now
            return remaining.days + (1 if remaining.seconds > 0 else 0)

    @staticmethod
    @db_retry
    async def is_pro(user_id: int) -> bool:
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(GroupSubscription).where(GroupSubscription.user_id == user_id))
            sub = res.scalar_one_or_none()
            if not sub:
                return False
            return sub.expires_at > datetime.now(UTC)

    @staticmethod
    @db_retry
    async def get_all_subscriptions() -> list[tuple[int, int]]:
        async with AsyncSessionLocal() as session:
            now = datetime.now(UTC)
            res = await session.execute(
                select(GroupSubscription.user_id, GroupSubscription.expires_at).where(GroupSubscription.expires_at > now)
            )
            subs = []
            for row in res.all():
                user_id = row[0]
                expires_at = row[1]
                remaining = expires_at - now
                days = remaining.days + (1 if remaining.seconds > 0 else 0)
                subs.append((user_id, days))
            return subs
            
    @staticmethod
    @db_retry
    async def get_all_keys() -> list[dict]:
        async with AsyncSessionLocal() as session:
            res = await session.execute(
                select(GroupActivationKey.key_string, GroupActivationKey.duration_days, GroupActivationKey.is_used, GroupActivationKey.used_by, GroupActivationKey.used_at, GroupActivationKey.expires_at)
            )
            keys = []
            for row in res.all():
                keys.append({
                    "key_string": row[0],
                    "duration_days": row[1],
                    "is_used": row[2],
                    "used_by": row[3],
                    "used_at": row[4],
                    "expires_at": row[5]
                })
            return keys

    @staticmethod
    @db_retry
    async def extend_subscription(user_id: int, days: int) -> bool:
        async with AsyncSessionLocal() as session, session.begin():
            res = await session.execute(select(GroupSubscription).where(GroupSubscription.user_id == user_id).with_for_update())
            sub = res.scalar_one_or_none()
            if not sub:
                return False
            sub.expires_at += timedelta(days=days)
            invalidate_tier_cache(user_id)
            return True

    @staticmethod
    @db_retry
    async def revoke_subscription(user_id: int) -> bool:
        async with AsyncSessionLocal() as session, session.begin():
            res = await session.execute(select(GroupSubscription).where(GroupSubscription.user_id == user_id).with_for_update())
            sub = res.scalar_one_or_none()
            if not sub:
                return False
            sub.expires_at = datetime.now(UTC) - timedelta(days=1)
            invalidate_tier_cache(user_id)
            return True
'''

with open('A:/projectmonolith/src/zenith_group_bot/repository.py', 'a', encoding='utf-8') as f:
    f.write(repo_code)
