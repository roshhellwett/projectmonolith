import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from group_bot.filters import is_inappropriate

logger = logging.getLogger("GROUP_BOT")

async def start_group_bot():
    token = os.getenv("GROUP_BOT_TOKEN")
    if not token:
        logger.error("GROUP_BOT_TOKEN missing!")
        return

    # FIX: Increased timeouts to prevent system-wide startup crash
    app = ApplicationBuilder().token(token).read_timeout(30).connect_timeout(30).build()

    async def group_monitor_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.text:
            return

        text = update.message.text
        user = update.effective_user
        chat_id = update.effective_chat.id

        # ULTRA SUPREME FILTERING
        violation, reason = is_inappropriate(text)

        if violation:
            try:
                # 1. Delete the message immediately
                await update.message.delete()
                
                # 2. Send a warning to the user
                warning = (
                    f"🛡️ <b>Ultra Supreme Shield</b>\n\n"
                    f"User: @{user.username if user.username else user.first_name}\n"
                    f"Action: <b>Message Deleted</b>\n"
                    f"Reason: {reason}"
                )
                await context.bot.send_message(chat_id=chat_id, text=warning, parse_mode="HTML")
                
                logger.info(f"VIOLATION: Deleted message from {user.id} in {chat_id}. Reason: {reason}")
                
            except Exception as e:
                logger.error(f"Failed to moderate message: {e}")

    # Monitor all text messages in groups
    app.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.TEXT, group_monitor_handler))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    logger.info("ULTRA SUPREME GROUP MONITOR ONLINE")