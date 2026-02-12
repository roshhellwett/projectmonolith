import os
import logging
import asyncio
import time
from telegram import Update, ChatPermissions
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from group_bot.filters import is_inappropriate
from group_bot.flood_control import is_flooding
from group_bot.violation_tracker import add_strike, MUTE_DURATION_SECONDS
from core.config import ADMIN_ID

logger = logging.getLogger("GROUP_BOT")

async def start_group_bot():
    token = os.getenv("GROUP_BOT_TOKEN")
    if not token:
        logger.error("GROUP_BOT_TOKEN missing!")
        return

    # High-stability network settings [cite: 46]
    app = ApplicationBuilder().token(token).read_timeout(30).connect_timeout(30).build()

    async def group_monitor_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.text:
            return

        text = update.message.text
        user = update.effective_user
        chat_id = update.effective_chat.id
        chat_title = update.effective_chat.title or "Private Group"

        # 1. Forensic Check (Abuse and Flooding) [cite: 41, 44, 47]
        # FIX: Added 'await' because is_inappropriate is now an async function
        violation, reason = await is_inappropriate(text)
        
        if not violation:
            violation, reason = is_flooding(user.id, text)

        if violation:
            try:
                # Delete the offensive message immediately [cite: 44, 47, 48]
                await update.message.delete()
                
                # Check for strikes and Mute if necessary [cite: 48]
                hit_limit = add_strike(user.id)
                
                if hit_limit:
                    # Execute 1-Hour Mute (Telegram Restriction) [cite: 49, 61]
                    until_date = int(time.time() + MUTE_DURATION_SECONDS)
                    await context.bot.restrict_chat_member(
                        chat_id=chat_id,
                        user_id=user.id,
                        permissions=ChatPermissions(can_send_messages=False),
                        until_date=until_date
                    )
                    
                    msg_text = f"🚫 <b>SUPREME MUTE APPLIED</b>\n\nUser: @{user.username}\nAction: <b>Restricted for 1 Hour</b>\nReason: Repeated Violations"
                    
                    # PRIVATE ADMIN NOTIFICATION [cite: 52]
                    admin_report = (
                        f"🛡️ <b>SECURITY ALERT: USER MUTED</b>\n"
                        f"<b>Group:</b> {chat_title}\n"
                        f"<b>User:</b> @{user.username} (<code>{user.id}</code>)\n"
                        f"<b>Reason:</b> {reason}\n"
                        f"<b>Duration:</b> 1 Hour"
                    )
                    await context.bot.send_message(chat_id=ADMIN_ID, text=admin_report, parse_mode="HTML")
                
                else:
                    msg_text = (
                        f"🛡️ <b>MESSAGE DELETED</b>\n\n"
                        f"User: @{user.username}\n"
                        f"Action: <b>Message Deleted</b>\n"
                        f"Reason: {reason}"
                    )

                # Send warning to the group [cite: 46, 55]
                warn_msg = await context.bot.send_message(chat_id=chat_id, text=msg_text, parse_mode="HTML")
                
                # Ghost Cleanup after 10 seconds [cite: 51, 56]
                await asyncio.sleep(10)
                await warn_msg.delete()
                
            except Exception as e:
                logger.error(f"Supreme Enforcement Error: {e}")

    # Monitor all text messages in groups [cite: 47]
    app.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.TEXT, group_monitor_handler))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    logger.info("ENFORCEMENT & ADMIN FEED ONLINE")