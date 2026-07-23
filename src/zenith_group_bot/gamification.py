import asyncio
import contextlib
from collections import defaultdict
from core.database import AsyncSessionLocal
from zenith_group_bot.models import GroupMemberStats
from core.logger import setup_logger
from sqlalchemy.future import select

logger = setup_logger("GAMIFICATION")

_xp_cache = defaultdict(int)
_msg_cache = defaultdict(int)
_rep_cache = defaultdict(int)

def add_xp_sync(user_id: int, chat_id: int, xp: int = 1):
    _xp_cache[(user_id, chat_id)] += xp
    _msg_cache[(user_id, chat_id)] += 1

def add_rep_sync(user_id: int, chat_id: int, rep: int = 1):
    _rep_cache[(user_id, chat_id)] += rep

async def flush_gamification():
    if not _xp_cache and not _rep_cache:
        return
        
    xp_snapshot = dict(_xp_cache)
    msg_snapshot = dict(_msg_cache)
    rep_snapshot = dict(_rep_cache)
    
    _xp_cache.clear()
    _msg_cache.clear()
    _rep_cache.clear()
    
    async with AsyncSessionLocal() as session:
        try:
            keys = set(xp_snapshot.keys()) | set(rep_snapshot.keys())
            for user_id, chat_id in keys:
                xp = xp_snapshot.get((user_id, chat_id), 0)
                msgs = msg_snapshot.get((user_id, chat_id), 0)
                rep = rep_snapshot.get((user_id, chat_id), 0)
                
                stmt = select(GroupMemberStats).where(
                    GroupMemberStats.user_id == user_id, GroupMemberStats.chat_id == chat_id
                )
                result = await session.execute(stmt)
                stat = result.scalar_one_or_none()
                
                if stat:
                    stat.xp += xp
                    stat.messages_sent += msgs
                    stat.reputation += rep
                    stat.level = (stat.xp // 100) + 1
                else:
                    stat = GroupMemberStats(
                        user_id=user_id, 
                        chat_id=chat_id, 
                        xp=xp, 
                        messages_sent=msgs,
                        reputation=rep,
                        level=(xp // 100) + 1
                    )
                    session.add(stat)
                    
            await session.commit()
        except Exception as e:
            logger.error(f"Error flushing gamification: {e}")
            await session.rollback()

async def gamification_loop():
    while True:
        await asyncio.sleep(60)
        await flush_gamification()
