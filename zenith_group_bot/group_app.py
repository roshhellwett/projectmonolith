import os
import logging
import asyncio
import traceback
from cachetools import TTLCache
from telegram import Update
from telegram.constants import MessageEntityType
from telegram.error import Forbidden, BadRequest
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, CallbackQueryHandler, ChatMemberHandler, filters, ContextTypes

from zenith_group_bot.setup_flow import cmd_setup, cmd_start_dm, button_handler, cmd_deletegroup
from zenith_group_bot.filters import is_inappropriate
from zenith_group_bot.flood_control import is_flooding
from zenith_group_bot.repository import init_group_db, MemberRepo, SettingsRepo, GroupRepo
from core.task_manager import fire_and_forget

logger = logging.getLogger("GROUP_BOT")
_group_app = None

# 🚀 SCENARIO 3: Admin Immunity Cache
admin_cache = TTLCache(maxsize=1000, ttl=900)
# 🚀 SCENARIO 18: Global Leaky Bucket (Max 25 outbound messages per second)
global_message_semaphore = asyncio.Semaphore(25)

async def is_user_admin(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int) -> bool:
    cache_key = f"{chat_id}_{user_id}"
    if cache_key in admin_cache: return admin_cache[cache_key]
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        is_admin = member.status in ["administrator", "creator"]
        admin_cache[cache_key] = is_admin
        return is_admin
    except Exception: return False

async def safe_delete(msg):
    try: await msg.delete()
    except BadRequest as e:
        # 🚀 SCENARIO 13: Rival Bot Race Condition Check
        if "message to delete not found" in str(e).lower(): pass
        else: raise

async def safe_send(context, chat_id, text, **kwargs):
    # 🚀 SCENARIO 18: Global outbound throttling
    async with global_message_semaphore:
        try:
            msg = await context.bot.send_message(chat_id=chat_id, text=text, **kwargs)
            await asyncio.sleep(0.04) # Enforces ~25 msg/sec global limit
            return msg
        except Exception: return None

async def trigger_circuit_breaker(e: Exception, chat_id: int, owner_id: int, group_name: str, context: ContextTypes.DEFAULT_TYPE):
    # 🚀 SCENARIO 9: Stealth Permission Strip Detector
    if "rights" in str(e).lower() or "permission" in str(e).lower():
        await SettingsRepo.upsert_settings(chat_id, owner_id, None, is_active=False)
        alert = f"🚨 <b>CIRCUIT BREAKER TRIGGERED</b>\nZenith's admin permissions were revoked in <b>{group_name}</b>. Monitoring has been halted to prevent bot crashes."
        await safe_send(context, owner_id, alert, parse_mode="HTML")

async def animate_and_delete(context: ContextTypes.DEFAULT_TYPE, message, seconds: int = 5):
    try:
        await asyncio.sleep(seconds)
        if message: await safe_delete(message)
    except Exception: pass

async def notify_owner(context: ContextTypes.DEFAULT_TYPE, chat_id: int, owner_id: int, group_name: str, username: str, reason: str, action: str):
    alert_text = f"🚨 <b>Zenith Security Alert</b>\n<b>Group:</b> {group_name}\n<b>User:</b> @{username}\n<b>Action:</b> {action}\n<b>Reason:</b> {reason}"
    try:
        await context.bot.send_message(chat_id=owner_id, text=alert_text, parse_mode="HTML")
    except Forbidden:
        fallback_text = f"🚨 <a href='tg://user?id={owner_id}'>Admin</a>, I caught a rule violation by @{username} but couldn't DM you because you blocked me! Please unblock me."
        await safe_send(context, chat_id, fallback_text, parse_mode="HTML")
    except Exception as e:
        logger.debug(f"Could not notify owner {owner_id}: {e}")

async def cmd_forgive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 🚀 SCENARIO 1: The Forgiveness Protocol
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    if update.effective_chat.type == "private": return
    if not await is_user_admin(context, chat_id, user_id): return
    if not update.message.reply_to_message: return await update.message.reply_text("⚠️ You must reply to the user's message to forgive them.")
        
    target_user = update.message.reply_to_message.from_user
    if target_user.is_bot: return

    await GroupRepo.forgive_user(target_user.id, chat_id)
    try: await context.bot.unban_chat_member(chat_id, target_user.id, only_if_banned=True)
    except Exception: pass
    await update.message.reply_text(f"✅ <b>Pardoned:</b> @{target_user.username}'s strike history has been wiped.", parse_mode="HTML")

async def my_chat_member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 🚀 SCENARIO 5: Ghost Kick Detector
    result = update.my_chat_member
    if result.new_chat_member.status in ["left", "kicked", "banned"]:
        chat_id = result.chat.id
        settings = await SettingsRepo.get_settings(chat_id)
        if settings and settings.is_active:
            await SettingsRepo.upsert_settings(chat_id, settings.owner_id, None, is_active=False)
            await safe_send(context, settings.owner_id, f"⚠️ I was removed from <b>{result.chat.title}</b>. Monitoring paused.", parse_mode="HTML")

async def handle_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            msg = "🛡️ <b>Zenith Group BOT has arrived.</b>\n\nTo activate:\n1. Promote me to <b>Administrator</b>.\n2. Type <code>/setup</code>"
            await safe_send(context, chat_id, msg, parse_mode="HTML")
            return 

    settings = await SettingsRepo.get_settings(chat_id)
    if not settings or not settings.is_active: return

    try: await update.message.delete()
    except Exception: pass 

    for member in update.message.new_chat_members:
        if not member.is_bot: await MemberRepo.register_new_member(member.id, chat_id)

async def group_monitor_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 🚀 SCENARIO 19: Poison Pill Safe Loop
    try:
        # 🚀 SCENARIO 2: Edited Message Capture
        msg = update.message or update.edited_message
        if not msg or msg.from_user.is_bot: return

        # 🚀 SCENARIO 7: Channel Identity & Anonymous Routing
        if msg.is_automatic_forward or msg.from_user.id == 1087968824: return
        if msg.sender_chat: return # Ignore anonymous admin posts / channel identities

        user = msg.from_user
        chat_id = update.effective_chat.id
        
        settings = await SettingsRepo.get_settings(chat_id)
        if not settings or not settings.is_active: return

        if await is_user_admin(context, chat_id, user.id): return

        # 🚀 SCENARIO 15 & 17: Pre-extract hidden markdown links before normalizer strips offsets
        hidden_urls = []
        for ent in (msg.entities or []) + (msg.caption_entities or []):
            if ent.type in [MessageEntityType.TEXT_LINK] and ent.url:
                hidden_urls.append(ent.url)
        
        raw_text = msg.text or msg.caption or ""
        text_to_scan = raw_text + " " + " ".join(hidden_urls)

        # 1. Anti-Raid / Quarantine Logic
        if settings.features in ["spam", "both"] and await MemberRepo.is_restricted(user.id, chat_id):
            has_media = bool(msg.photo or msg.video or msg.document or msg.audio or msg.sticker or msg.animation)
            has_link = any(e.type in [MessageEntityType.URL, MessageEntityType.TEXT_LINK] for e in (msg.entities or []) + (msg.caption_entities or []))
            if has_media or has_link:
                try: 
                    await safe_delete(msg)
                    alert = await safe_send(context, chat_id, f"🛡️ <b>Anti-Raid Active:</b>\n@{user.username}, new members cannot send links/media for 24 hours.", parse_mode="HTML")
                    fire_and_forget(animate_and_delete(context, alert, seconds=5))
                    await notify_owner(context, chat_id, settings.owner_id, settings.group_name, user.username, "Quarantine Link/Media Attempt", "Deleted")
                except BadRequest as e: 
                    await trigger_circuit_breaker(e, chat_id, settings.owner_id, settings.group_name, context)
                return 

        # 2. Main Filtering Logic
        violation, reason = False, ""
        if settings.features in ["abuse", "both"]:
            violation, reason = await is_inappropriate(text_to_scan) 
        
        if settings.features in ["spam", "both"] and not violation and raw_text: 
            violation, reason = is_flooding(user.id, msg.media_group_id)
    
        if violation:
            try:
                await safe_delete(msg)
                strikes = await GroupRepo.process_violation(user.id, chat_id)
                if strikes >= 3:
                    await context.bot.ban_chat_member(chat_id, user.id)
                    alert = await safe_send(context, chat_id, f"🚨 <b>BANNED:</b> @{user.username} for repeated violations.", parse_mode="HTML")
                    await notify_owner(context, chat_id, settings.owner_id, settings.group_name, user.username, reason, "BANNED")
                else:
                    alert = await safe_send(context, chat_id, f"🛡️ <b>WARNING:</b> @{user.username}, message deleted. Strike {strikes}/3.", parse_mode="HTML")
                    await notify_owner(context, chat_id, settings.owner_id, settings.group_name, user.username, reason, f"Deleted (Strike {strikes})")
                
                fire_and_forget(animate_and_delete(context, alert, seconds=5))
            except BadRequest as e:
                await trigger_circuit_breaker(e, chat_id, settings.owner_id, settings.group_name, context)
                
    except Exception as e:
        logger.error(f"POISON PILL CAUGHT: {e}\n{traceback.format_exc()}")

# 🚀 REFACTORED FOR WEBHOOK MONOLITH
async def setup_group_app():
    """Builds the PTB application but does not start polling."""
    token = os.getenv("GROUP_BOT_TOKEN")
    await init_group_db()

    app = ApplicationBuilder().token(token).build()
    
    app.add_handler(CommandHandler("start", cmd_start_dm))
    app.add_handler(CommandHandler("setup", cmd_setup))
    app.add_handler(CommandHandler("deletegroup", cmd_deletegroup))
    app.add_handler(CommandHandler("forgive", cmd_forgive))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(ChatMemberHandler(my_chat_member_handler, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_members))
    app.add_handler(MessageHandler(filters.ChatType.GROUPS & (~filters.COMMAND) & (~filters.StatusUpdate.ALL), group_monitor_handler))

    return app