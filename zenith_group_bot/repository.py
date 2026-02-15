from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, delete, update
from datetime import timedelta
from cachetools import TTLCache

from zenith_group_bot.models import Base, GroupStrike, NewMember, GroupSettings
from core.config import DATABASE_URL, DB_POOL_SIZE
from utils.time_util import utc_now

engine = create_async_engine(DATABASE_URL, pool_size=DB_POOL_SIZE, max_overflow=20, pool_pre_ping=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

settings_cache = TTLCache(maxsize=1000, ttl=300)      
quarantine_cache = TTLCache(maxsize=50000, ttl=3600)  

async def init_group_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def dispose_group_engine():
    await engine.dispose()

class SettingsRepo:
    @staticmethod
    async def get_settings(chat_id: int):
        if chat_id in settings_cache: return settings_cache[chat_id]
        async with AsyncSessionLocal() as session:
            stmt = select(GroupSettings).where(GroupSettings.chat_id == chat_id)
            record = (await session.execute(stmt)).scalar_one_or_none()
            if record: settings_cache[chat_id] = record
            return record

    @staticmethod
    async def get_owned_groups(owner_id: int):
        async with AsyncSessionLocal() as session:
            stmt = select(GroupSettings).where(GroupSettings.owner_id == owner_id)
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    async def upsert_settings(chat_id: int, owner_id: int, group_name: str, features: str = None, strength: str = None, is_active: bool = None):
        async with AsyncSessionLocal() as session:
            stmt = select(GroupSettings).where(GroupSettings.chat_id == chat_id)
            record = (await session.execute(stmt)).scalar_one_or_none()
            
            if not record:
                record = GroupSettings(chat_id=chat_id, owner_id=owner_id, group_name=group_name)
                session.add(record)
            
            if features: record.features = features
            if strength: record.strength = strength
            if is_active is not None: record.is_active = is_active
            
            await session.commit()
            settings_cache[chat_id] = record
            return record

    @staticmethod
    async def set_active_status(chat_id: int, is_active: bool):
        async with AsyncSessionLocal() as session:
            stmt = select(GroupSettings).where(GroupSettings.chat_id == chat_id)
            record = (await session.execute(stmt)).scalar_one_or_none()
            if record:
                record.is_active = is_active
                await session.commit()
                settings_cache[chat_id] = record
            return record

    @staticmethod
    async def migrate_chat_id(old_id: int, new_id: int):
        async with AsyncSessionLocal() as session:
            await session.execute(update(GroupSettings).where(GroupSettings.chat_id == old_id).values(chat_id=new_id))
            await session.execute(update(GroupStrike).where(GroupStrike.chat_id == old_id).values(chat_id=new_id))
            await session.execute(update(NewMember).where(NewMember.chat_id == old_id).values(chat_id=new_id))
            await session.commit()
            settings_cache.pop(old_id, None)

    @staticmethod
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
    async def process_violation(user_id: int, chat_id: int):
        async with AsyncSessionLocal() as session:
            stmt = select(GroupStrike).where(GroupStrike.user_id == user_id, GroupStrike.chat_id == chat_id)
            record = (await session.execute(stmt)).scalar_one_or_none()
            if not record:
                record = GroupStrike(user_id=user_id, chat_id=chat_id, strike_count=1, last_violation=utc_now())
                session.add(record)
            else:
                record.strike_count += 1
                record.last_violation = utc_now()
            await session.commit()
            return record.strike_count

class MemberRepo:
    @staticmethod
    async def register_new_member(user_id: int, chat_id: int):
        async with AsyncSessionLocal() as session:
            stmt = select(NewMember).where(NewMember.user_id == user_id, NewMember.chat_id == chat_id)
            record = (await session.execute(stmt)).scalar_one_or_none()
            if not record:
                record = NewMember(user_id=user_id, chat_id=chat_id, joined_at=utc_now())
                session.add(record)
            else:
                record.joined_at = utc_now()
            await session.commit()
            quarantine_cache.pop(f"{chat_id}_{user_id}", None)

    @staticmethod
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