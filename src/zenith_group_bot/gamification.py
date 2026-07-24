import asyncio
import contextlib
from collections import defaultdict
from core.database import AsyncSessionLocal
from zenith_group_bot.models import GroupMemberStats
from core.logger import setup_logger
from sqlalchemy.future import select
from sqlalchemy import desc
from telegram import Update
from telegram.ext import ContextTypes
import html
import time
from cachetools import TTLCache

logger = setup_logger("GAMIFICATION")

_xp_cache = defaultdict(int)
_msg_cache = defaultdict(int)
_rep_cache = defaultdict(int)

_last_xp_time = TTLCache(maxsize=10000, ttl=60)
_last_rep_time = TTLCache(maxsize=10000, ttl=300)

def add_xp_sync(user_id: int, chat_id: int, xp: int = 1):
    _msg_cache[(user_id, chat_id)] += 1
    
    # Cooldown check for XP (1 minute)
    key = (user_id, chat_id)
    if key in _last_xp_time:
        return False
    
    _last_xp_time[key] = time.time()
    _xp_cache[key] += xp
    return True

def add_rep_sync(user_id: int, chat_id: int, rep: int = 1):
    _rep_cache[(user_id, chat_id)] += rep

def can_give_rep(giver_id: int, chat_id: int) -> bool:
    key = (giver_id, chat_id)
    if key in _last_rep_time:
        return False
    _last_rep_time[key] = time.time()
    return True

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

async def get_user_stats(user_id: int, chat_id: int):
    async with AsyncSessionLocal() as session:
        stmt = select(GroupMemberStats).where(GroupMemberStats.user_id == user_id, GroupMemberStats.chat_id == chat_id)
        result = await session.execute(stmt)
        stat = result.scalar_one_or_none()
        
        xp = stat.xp if stat else 0
        level = stat.level if stat else 1
        rep = stat.reputation if stat else 0
        msgs = stat.messages_sent if stat else 0
        
        cache_key = (user_id, chat_id)
        xp += _xp_cache.get(cache_key, 0)
        rep += _rep_cache.get(cache_key, 0)
        msgs += _msg_cache.get(cache_key, 0)
        level = (xp // 100) + 1
        
        return xp, level, rep, msgs

async def get_top_users(chat_id: int, limit: int = 10):
    async with AsyncSessionLocal() as session:
        stmt = select(GroupMemberStats).where(GroupMemberStats.chat_id == chat_id).order_by(desc(GroupMemberStats.xp)).limit(limit)
        result = await session.execute(stmt)
        return result.scalars().all()

async def cmd_me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    if chat.type == "private":
        return await update.message.reply_text("This command is only available in groups.")
        
    xp, level, rep, msgs = await get_user_stats(user.id, chat.id)
    text = (
        f"👤 <b>{html.escape(user.first_name)}'s Profile</b>\n\n"
        f"🔰 <b>Level:</b> {level}\n"
        f"💠 <b>XP:</b> {xp}\n"
        f"🌟 <b>Reputation:</b> {rep}\n"
        f"💬 <b>Messages:</b> {msgs}"
    )
    await update.message.reply_text(text, parse_mode="HTML")

async def cmd_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type == "private":
        return await update.message.reply_text("This command is only available in groups.")
        
    top_users = await get_top_users(chat.id)
    if not top_users:
        return await update.message.reply_text("No gamification data available yet.")
        
    lines = [f"🏆 <b>Top Members of {html.escape(chat.title)}</b>\n"]
    for idx, stat in enumerate(top_users, 1):
        medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"{idx}."
        user_mention = f"<a href='tg://user?id={stat.user_id}'>User {stat.user_id}</a>"
        lines.append(f"{medal} {user_mention} - Lvl {stat.level} (XP: {stat.xp}, Rep: {stat.reputation})")
        
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")
