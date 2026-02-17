import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from core.config import DATABASE_URL, DB_POOL_SIZE
from zenith_crypto_bot.models import CryptoBase, Subscription, ActivationKey

engine = create_async_engine(DATABASE_URL, pool_size=DB_POOL_SIZE)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_crypto_db():
    async with engine.begin() as conn:
        await conn.run_sync(CryptoBase.metadata.create_all)

class SubscriptionRepo:

    @staticmethod
    async def get_all_active_users():
        async with AsyncSessionLocal() as session:
            now = datetime.now(timezone.utc)

            res = await session.execute(
                select(Subscription.user_id).where(
                    Subscription.expires_at > now
                )
            )

            return [r[0] for r in res.all()]

    @staticmethod
    async def generate_key(days: int) -> str:
        new_key = f"ZENITH-{uuid.uuid4().hex[:8].upper()}-{uuid.uuid4().hex[:4].upper()}"
        async with AsyncSessionLocal() as session:
            session.add(ActivationKey(key_string=new_key, duration_days=days))
            await session.commit()
        return new_key

    @staticmethod
    async def redeem_key(user_id: int, key_string: str) -> tuple[bool, str]:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                res = await session.execute(select(ActivationKey).where(ActivationKey.key_string == key_string).with_for_update())
                key = res.scalar_one_or_none()
                
                if not key or key.is_used: 
                    return False, "❌ Invalid or already used key."
                
                key.is_used = True
                key.used_by = user_id
                
                res = await session.execute(select(Subscription).where(Subscription.user_id == user_id).with_for_update())
                sub = res.scalar_one_or_none()
                
                # 🚀 SRE FIX: Strict UTC Awareness
                now = datetime.now(timezone.utc)
                add_on = timedelta(days=key.duration_days)
                
                if sub and sub.expires_at > now:
                    sub.expires_at += add_on 
                else:
                    new_expiry = now + add_on
                    if sub: sub.expires_at = new_expiry
                    else: session.add(Subscription(user_id=user_id, expires_at=new_expiry))
                    
                return True, f"✅ Activated! {key.duration_days} days added to your account."

    @staticmethod
    async def get_days_left(user_id: int) -> int:
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(Subscription).where(Subscription.user_id == user_id))
            sub = res.scalar_one_or_none()
            
            now = datetime.now(timezone.utc)
            if not sub or sub.expires_at < now:
                return 0
            return (sub.expires_at - now).days

async def dispose_crypto_engine():
    await engine.dispose()