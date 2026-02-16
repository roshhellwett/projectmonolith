import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, delete, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from datetime import timedelta
from cachetools import TTLCache

from zenith_group_bot.models import Base, GroupStrike, NewMember, GroupSettings
from core.config import DATABASE_URL, DB_POOL_SIZE
from utils.time_util import utc_now
from core.logger import setup_logger

logger = setup_logger("DB_REPO")

engine = create_async_engine(DATABASE_URL, pool_size=DB_POOL_SIZE, max_overflow=20, pool_pre_ping=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

settings_cache = TTLCache(maxsize=1000, ttl=300)
# 🚀 SCENARIO 12: Thundering Herd Mutex Lock
settings_lock = asyncio.Lock()      

quarantine_cache = TTLCache(maxsize=50000, ttl=3600)  
# 🚀 SCENARIO 14: Debounce cache to stop Bouncing Trolls
join_debounce = TTLCache(maxsize=10000, ttl=60) 

async def init_group_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def dispose_group_engine():
    await engine.dispose()

# 🚀 SCENARIO 10: Exponential Backoff for Network Blips
def db_retry(func):
    async def wrapper(*args, **kwargs):
        for attempt in range(3):
            try: return await func(*args, **kwargs)
            except Exception as e:
                if attempt == 2: raise
                logger.warning(f"DB Network Blip in {func.__name__}, retrying... ({e})")
                await asyncio.sleep(0.5 * (2 ** attempt))
    return wrapper

class SettingsRepo:
    @staticmethod
    @db_retry
    async def get_settings(chat_id: int):
        if chat_id in settings_cache: return settings_cache[chat_id]
        
        # 🚀 SCENARIO 12: Mutex lock prevents connection pool exhaustion
        async with settings_lock:
            if chat_id in settings_cache: return settings_cache[chat_id]
            
            # 🚀 SCENARIO 16: Ultra-fast DB Context Management
            async with AsyncSessionLocal() as session:
                stmt = select(GroupSettings).where(GroupSettings.chat_id == chat_id)
                record = (await session.execute(stmt)).scalar_one_or_none()
                if record: settings_cache[chat_id] = record
                return record

    @staticmethod
    @db_retry
    async def get_owned_groups(owner_id: int):
        async with AsyncSessionLocal() as session:
            stmt = select(GroupSettings).where(GroupSettings.owner_id == owner_id)
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    @db_retry
    async def upsert_settings(chat_id: int, owner_id: int, group_name: str, features: str = None, strength: str = None, is_active: bool = None):
        async with AsyncSessionLocal() as session:
            stmt = pg_insert(GroupSettings).values(
                chat_id=chat_id, owner_id=owner_id, group_name=group_name, 
                features=features or "both", strength=strength or "medium", is_active=is_active or False
            )
            update_dict = {}
            if features: update_dict['features'] = features
            if strength: update_dict['strength'] = strength
            if is_active is not None: update_dict['is_active'] = is_active
            if group_name: update_dict['group_name'] = group_name

            if update_dict: stmt = stmt.on_conflict_do_update(index_elements=['chat_id'], set_=update_dict)
            else: stmt = stmt.on_conflict_do_nothing()
                
            await session.execute(stmt)
            await session.commit()
            
            res = await session.execute(select(GroupSettings).where(GroupSettings.chat_id == chat_id))
            record = res.scalar_one()
            settings_cache[chat_id] = record
            return record

    @staticmethod
    @db_retry
    async def wipe_group_container(chat_id: int, owner_id: int) -> bool:
        async with AsyncSessionLocal() as session:
            stmt = select(GroupSettings).where(GroupSettings.chat_id == chat_id, GroupSettings.owner_id == owner_id)
            if not (await session.execute(stmt)).scalar_one_or_none(): return False
            await session.execute(delete(GroupStrike).where(GroupStrike.chat_id == chat_id))
            await session.execute(delete(NewMember).where(NewMember.chat_id == chat_id))
            await session.execute(delete(GroupSettings).where(GroupSettings.chat_id == chat_id))
            await session.commit()
            settings_cache.pop(chat_id, None)
            return True

class GroupRepo:
    @staticmethod
    @db_retry
    async def process_violation(user_id: int, chat_id: int) -> int:
        async with AsyncSessionLocal() as session:
            stmt = pg_insert(GroupStrike).values(
                user_id=user_id, chat_id=chat_id, strike_count=1, last_violation=utc_now()
            ).on_conflict_do_update(
                index_elements=['user_id', 'chat_id'],
                set_=dict(strike_count=GroupStrike.strike_count + 1, last_violation=utc_now())
            ).returning(GroupStrike.strike_count)
            result = await session.execute(stmt)
            await session.commit()
            return result.scalar()

    @staticmethod
    @db_retry
    async def forgive_user(user_id: int, chat_id: int) -> bool:
        async with AsyncSessionLocal() as session:
            stmt = delete(GroupStrike).where(GroupStrike.user_id == user_id, GroupStrike.chat_id == chat_id)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

class MemberRepo:
    @staticmethod
    @db_retry
    async def register_new_member(user_id: int, chat_id: int):
        cache_key = f"{chat_id}_{user_id}"
        # 🚀 SCENARIO 14: Debounce checks stop DB spam from trolls leaving/joining rapidly
        if cache_key in join_debounce: return
        join_debounce[cache_key] = True

        async with AsyncSessionLocal() as session:
            stmt = pg_insert(NewMember).values(
                user_id=user_id, chat_id=chat_id, joined_at=utc_now()
            ).on_conflict_do_update(index_elements=['user_id', 'chat_id'], set_=dict(joined_at=utc_now()))
            await session.execute(stmt)
            await session.commit()
            quarantine_cache.pop(cache_key, None)

    @staticmethod
    @db_retry
    async def is_restricted(user_id: int, chat_id: int) -> bool:
        cache_key = f"{chat_id}_{user_id}"
        if quarantine_cache.get(cache_key) == "CLEARED": return False
        
        async with AsyncSessionLocal() as session:
            stmt = select(NewMember).where(NewMember.user_id == user_id, NewMember.chat_id == chat_id)
            record = (await session.execute(stmt)).scalar_one_or_none()
            if record and (utc_now() - record.joined_at) < timedelta(hours=24):
                return True
            quarantine_cache[cache_key] = "CLEARED"
            return False