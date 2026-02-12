import os
import logging
import asyncio
import time
from telegram import Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes, CommandHandler
from group_bot.filters import is_inappropriate
from group_bot.flood_control import is_flooding
from group_bot.violation_tracker import add_strike, MUTE_DURATION_SECONDS
from core.config import ADMIN_ID

logger = logging.getLogger("GROUP_BOT")

# Performance Config for High-Traffic (2000+ members)
WELCOME_COOLDOWN = 30  
last_welcome_time = 0

async def start_group_bot():
    token = os.getenv("GROUP_BOT_TOKEN")
    if not token:
        logger.error("GROUP_BOT_TOKEN missing!")
        return

    app = ApplicationBuilder().token(token).read_timeout(30).connect_timeout(30).build()

    async def send_welcome_hub(chat_id, context: ContextTypes.DEFAULT_TYPE):
        """Unified Hub Menu: Updated with Rules and Links."""
        keyboard = [
            [InlineKeyboardButton("📢 Official Notification Channel", url="https://t.me/teleacademicbot")],
            [InlineKeyboardButton("🔍 Search Past Notices (Search Bot)", url="https://t.me/makautsearchbot")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = (
            "🎓 <b>MAKAUT Student Hub & Rules</b>\n\n"
            "<b>Quick Links:</b>\n"
            "1. Check the <b>Channel</b> for real-time alerts.\n"
            "2. Use the <b>Search Bot</b> to find specific documents.\n\n"
            "<b>⚖️ Group Rules:</b>\n"
            "• No abusive language or personal attacks.\n"
            "• No spamming or unauthorized links.\n"
            "• 3 Strikes = 1 Hour Mute automatically.\n\n"
            "<i>Pin this message for easy access!</i>"
        )
        return await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML", reply_markup=reply_markup)

    async def help_hub(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manual /help command to show the Hub Menu."""
        await send_welcome_hub(update.effective_chat.id, context)

    async def welcome_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Auto-Welcome: Throttled to prevent crashes during member rushes."""
        global last_welcome_time
        now = time.time()

        if now - last_welcome_time > WELCOME_COOLDOWN:
            last_welcome_time = now
            await send_welcome_hub(update.effective_chat.id, context)

    async def group_monitor_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Forensic Message Monitor with Strike Enforcement."""
        if not update.message or not update.message.text:
            return

        text = update.message.text
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        violation, reason = await is_inappropriate(text)
        if not violation:
            violation, reason = is_flooding(user.id, text)

        if violation:
            try:
                await update.message.delete()
                hit_limit = await add_strike(user.id)
                
                if hit_limit:
                    until_date = int(time.time() + MUTE_DURATION_SECONDS)
                    await context.bot.restrict_chat_member(
                        chat_id=chat_id, 
                        user_id=user.id,
                        permissions=ChatPermissions(can_send_messages=False),
                        until_date=until_date
                    )
                    
                    admin_report = f"🛡️ <b>SECURITY ALERT</b>\nUser: @{user.username}\nReason: {reason}"
                    await context.bot.send_message(chat_id=ADMIN_ID, text=admin_report, parse_mode="HTML")
                    msg_text = f"🚫 <b>SUPREME MUTE</b>\nUser: @{user.username}\nReason: Repeated Violations"
                else:
                    msg_text = f"🛡️ <b>MESSAGE DELETED</b>\nReason: {reason}"

                warn_msg = await context.bot.send_message(chat_id=chat_id, text=msg_text, parse_mode="HTML")
                await asyncio.sleep(10)
                await warn_msg.delete()
            except Exception as e:
                logger.error(f"Enforcement Error: {e}")

    # Registering Handlers
    app.add_handler(CommandHandler("help", help_hub))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_handler))
    app.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.TEXT, group_monitor_handler))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    logger.info("UNIFIED GROUP HUB ONLINE")