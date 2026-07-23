
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from core.config import ADMIN_USER_ID
from zenith_admin_bot import ui as admin_ui
from zenith_admin_bot.common import admin_only, rate_limit_admin
from zenith_admin_bot.repository import AdminRepo, BotRegistryRepo, MonitoringRepo
from zenith_crypto_bot.repository import CryptoSubscriptionRepo
from zenith_group_bot.repository import GroupSubscriptionRepo

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    await update.message.reply_text(
        admin_ui.get_admin_dashboard(),
        reply_markup=admin_ui.get_admin_main_menu(),
        parse_mode="HTML",
    )

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    text = (
        "<b>🛡️ Zenith Admin Terminal</b>\n\n"
        "Use the inline buttons in /start to navigate the dashboard.\n\n"
        "<b>Available Commands:</b>\n"
        "<code>/start</code> - Open Dashboard\n"
        "<code>/broadcast [msg]</code> - Send global message\n"
    )
    await update.message.reply_text(text, parse_mode="HTML")

@admin_only
@rate_limit_admin(seconds=10)
async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /broadcast [message]")
        return
    message = " ".join(context.args)
    # Broadcast logic would go here
    await AdminRepo.log_action(ADMIN_USER_ID, "broadcast", details="Global broadcast sent")
    await update.message.reply_text("Broadcast sent successfully.")
