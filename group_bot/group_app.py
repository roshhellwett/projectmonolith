import os
import logging
import asyncio
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes, CommandHandler
from group_bot.filters import is_inappropriate
from group_bot.flood_control import is_flooding
from group_bot.violation_tracker import add_strike, MUTE_DURATION_SECONDS
from core.config import ADMIN_ID

logger = logging.getLogger("GROUP_BOT")
WELCOME_COOLDOWN = 30  
last_welcome_time = 0

async def announce_maintenance(context, chat_id, is_start=True):
    try:
        status_text = "🚧 <b>MAINTENANCE MODE:</b> Services suspended for updates." if is_start else "✅ <b>ONLINE:</b> Services resumed."
        msg = await context.bot.send_message(chat_id=chat_id, text=status_text, parse_mode="HTML")
        if not is_start:
            async def auto_delete():
                await asyncio.sleep(60)
                try: await msg.delete()
                except: pass
            asyncio.create_task(auto_delete())
    except Exception as e:
        logger.error(f"Announcement Error: {e}")

async def start_group_bot():
    token = os.getenv("GROUP_BOT_TOKEN")
    if not token: return

    app = ApplicationBuilder().token(token).read_timeout(30).connect_timeout(30).build()

    async def send_welcome_hub(chat_id, context):
        keyboard = [[InlineKeyboardButton("📢 Official Channel", url="https://t.me/teleacademicbot")],
                    [InlineKeyboardButton("🔍 Search Bot", url="https://t.me/makautsearchbot")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = "🎓 <b>Academic Group & Rules</b>\n\n⚖️ <b>Rules:</b> No abuse, no spam."
        return await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML", reply_markup=reply_markup)

    async def welcome_handler(update: Update, context):
        global last_welcome_time
        if time.time() - last_welcome_time > WELCOME_COOLDOWN:
            last_welcome_time = time.time()
            welcome_msg = await send_welcome_hub(update.effective_chat.id, context)
            async def auto_delete():
                await asyncio.sleep(20)
                try: await welcome_msg.delete()
                except: pass
            asyncio.create_task(auto_delete())

    async def group_monitor_handler(update: Update, context):
        if not update.message or not update.message.text: return
        text, user, chat_id = update.message.text, update.effective_user, update.effective_chat.id
        
        violation, reason = await is_inappropriate(text)
        if not violation: violation, reason = is_flooding(user.id, text)
        
        if violation:
            try:
                await update.message.delete()
                hit_limit = await add_strike(user.id)
                msg = f"🚫 <b>RESTRICTED</b>: @{user.username}" if hit_limit else f"🛡️ <b>DELETED</b>: {reason}"
                warn = await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML")
                await asyncio.sleep(10)
                await warn.delete()
            except Exception as e: logger.error(f"Monitor Error: {e}")

    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_handler))
    app.add_handler(CommandHandler("help", lambda u, c: send_welcome_hub(u.effective_chat.id, c)))
    app.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.TEXT, group_monitor_handler))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    logger.info("GROUP HUB ONLINE")
#@academictelebotbyroshhellwett