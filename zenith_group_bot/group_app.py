import os
import logging
import asyncio
from telegram import Update
from telegram.constants import MessageEntityType
from telegram.error import Forbidden, BadRequest
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, CallbackQueryHandler, ChatMemberHandler, filters, ContextTypes

from zenith_group_bot.setup_flow import cmd_setup, cmd_start_dm, button_handler, cmd_deletegroup
from zenith_group_bot.filters import is_inappropriate
from zenith_group_bot.flood_control import is_flooding
from zenith_group_bot.repository import init_group_db, MemberRepo, SettingsRepo, GroupRepo

logger = logging.getLogger("GROUP_BOT")

async def animate_and_delete(context: ContextTypes.DEFAULT_TYPE, message, seconds: int = 5):
    try:
        await asyncio.sleep(seconds)
        await context.bot.delete_message(chat_id=message.chat_id, message_id=message.message_id)
    except Exception: pass

async def notify_owner(context: ContextTypes.DEFAULT_TYPE, chat_id: int, owner_id: int, group_name: str, username: str, reason: str, action: str):
    alert_text = f"🚨 <b>Zenith Security Alert</b>\n<b>Group:</b> {group_name}\n<b>User:</b> @{username}\n<b>Action:</b> {action}\n<b>Reason:</b> {reason}"
    try:
        await context.bot.send_message(chat_id=owner_id, text=alert_text, parse_mode="HTML")
    except Forbidden:
        # Scenario 4: The Silent Treatment (Owner blocked the bot). Fallback to public tag.
        fallback_text = f"🚨 <a href='tg://user?id={owner_id}'>Admin</a>, I caught a rule violation by @{username} but couldn't DM you because you blocked me! Please unblock me."
        try: await context.bot.send_message(chat_id=chat_id, text=fallback_text, parse_mode="HTML")
        except: pass
    except Exception as e:
        logger.debug(f"Could not notify owner {owner_id}: {e}")

# Scenario 2: The Ghost Town (Bot gets kicked)
async def my_chat_member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.my_chat_member
    if result.new_chat_member.status in ["left", "kicked", "banned"]:
        chat_id = result.chat.id
        settings = await SettingsRepo.get_settings(chat_id)
        if settings and settings.is_active:
            await SettingsRepo.set_active_status(chat_id, False)
            try: await context.bot.send_message(settings.owner_id, f"⚠️ I was removed from <b>{result.chat.title}</b>. Monitoring paused.", parse_mode="HTML")
            except: pass

# Scenario 3: Identity Crisis (Group upgraded to Supergroup)
async def handle_migration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    old_id = update.message.migrate_from_chat_id
    new_id = update.message.chat_id
    if old_id and new_id:
        await SettingsRepo.migrate_chat_id(old_id, new_id)
        logger.info(f"🔄 Migrated ID {old_id} -> {new_id}")

async def handle_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            msg = "🛡️ <b>Zenith Group BOT has arrived.</b>\n\nTo activate:\n1. Promote me to <b>Administrator</b>.\n2. Type <code>/setup</code>"
            await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML")
            return 

    settings = await SettingsRepo.get_settings(chat_id)
    if not settings or not settings.is_active: return

    try: await update.message.delete()
    except Exception: pass 

    for member in update.message.new_chat_members:
        if not member.is_bot:
            await MemberRepo.register_new_member(member.id, chat_id)

async def group_monitor_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.message.from_user.is_bot: return
    msg = update.message

    # Scenario 8: Anonymous Admin & Linked Channel Bypass
    if msg.is_automatic_forward or msg.sender_chat or msg.from_user.id == 1087968824:
        return

    user = update.effective_user
    chat_id = update.effective_chat.id
    settings = await SettingsRepo.get_settings(chat_id)
    if not settings or not settings.is_active: return

    text = msg.text or msg.caption or ""

    if settings.features in ["spam", "both"] and await MemberRepo.is_restricted(user.id, chat_id):
        has_media = bool(msg.photo or msg.video or msg.document or msg.audio or msg.sticker or msg.animation)
        has_link = any(e.type in [MessageEntityType.URL, MessageEntityType.TEXT_LINK] for e in (msg.entities or []) + (msg.caption_entities or []))
        if has_media or has_link:
            try: 
                await msg.delete()
                alert = await context.bot.send_message(chat_id=chat_id, text=f"🛡️ <b>Anti-Raid Active:</b>\n@{user.username}, new members cannot send links/media for 24 hours.", parse_mode="HTML")
                context.application.create_task(animate_and_delete(context, alert, seconds=5))
                await notify_owner(context, chat_id, settings.owner_id, settings.group_name, user.username, "Quarantine Media/Link Attempt", "Deleted Message")
            except BadRequest: 
                # Scenario 6: Demoted Bot
                await notify_owner(context, chat_id, settings.owner_id, settings.group_name, user.username, "Quarantine Hit", "FAILED - Missing Delete Permission!")
            return 

    violation, reason = False, ""
    
    if settings.features in ["abuse", "both"]:
        violation, reason = await is_inappropriate(text) 
    
    if settings.features in ["spam", "both"] and not violation and text: 
        violation, reason = is_flooding(user.id, msg.media_group_id) # Passed media_group_id for Album Fix
    
    if violation:
        try:
            await msg.delete()
            strikes = await GroupRepo.process_violation(user.id, chat_id)
            if strikes >= 3:
                await context.bot.ban_chat_member(chat_id, user.id)
                alert = await context.bot.send_message(chat_id=chat_id, text=f"🚨 <b>BANNED:</b> @{user.username} for repeated violations.", parse_mode="HTML")
                await notify_owner(context, chat_id, settings.owner_id, settings.group_name, user.username, reason, "BANNED USER")
            else:
                alert = await context.bot.send_message(chat_id=chat_id, text=f"🛡️ <b>WARNING:</b> @{user.username}, message deleted. Strike {strikes}/3.", parse_mode="HTML")
                await notify_owner(context, chat_id, settings.owner_id, settings.group_name, user.username, reason, f"Deleted Message (Strike {strikes})")
            context.application.create_task(animate_and_delete(context, alert, seconds=5))
        except BadRequest as e:
            # Scenario 6: Demoted Bot
            if "delete" in str(e).lower() or "restrict" in str(e).lower():
                await notify_owner(context, chat_id, settings.owner_id, settings.group_name, user.username, reason, "FAILED ENFORCEMENT - Admin Rights Revoked!")
        except Exception as e: 
            logger.error(f"Moderation Error: {e}")

async def start_group_bot():
    token = os.getenv("GROUP_BOT_TOKEN")
    await init_group_db()

    app = ApplicationBuilder().token(token).build()
    
    app.add_handler(CommandHandler("start", cmd_start_dm))
    app.add_handler(CommandHandler("setup", cmd_setup))
    app.add_handler(CommandHandler("deletegroup", cmd_deletegroup))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # Core Scenarios Handlers
    app.add_handler(ChatMemberHandler(my_chat_member_handler, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.StatusUpdate.MIGRATE, handle_migration))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_members))
    app.add_handler(MessageHandler(filters.ChatType.GROUPS & (~filters.COMMAND) & (~filters.StatusUpdate.ALL), group_monitor_handler))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    logger.info("ZENITH SUPREME SAAS: ALL SHIELDS ONLINE")
    await asyncio.Event().wait()