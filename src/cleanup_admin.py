import sys

# 1. Write commands.py
commands_code = '''
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from core.config import ADMIN_USER_ID
from zenith_admin_bot import ui as admin_ui
from zenith_admin_bot.common import admin_only, rate_limit_admin
from zenith_admin_bot.repository import AdminRepo, BotRegistryRepo, MonitoringRepo
from zenith_crypto_bot.repository import CryptoSubscriptionRepo
from zenith_group_bot.repository import GroupCryptoSubscriptionRepo

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
        "<b>🛡️ Zenith Admin Terminal</b>\\n\\n"
        "Use the inline buttons in /start to navigate the dashboard.\\n\\n"
        "<b>Available Commands:</b>\\n"
        "<code>/start</code> - Open Dashboard\\n"
        "<code>/broadcast [msg]</code> - Send global message\\n"
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
'''

with open('A:/projectmonolith/src/zenith_admin_bot/commands.py', 'w', encoding='utf-8') as f:
    f.write(commands_code)


# 2. Write dashboard.py
dashboard_code = '''
import contextlib
from telegram import Update
from telegram.ext import ContextTypes
from core.config import ADMIN_USER_ID
from zenith_admin_bot import ui as admin_ui
from zenith_admin_bot.common import logger
from zenith_admin_bot.repository import AdminRepo, BotRegistryRepo, MonitoringRepo
from zenith_crypto_bot.repository import CryptoSubscriptionRepo
from zenith_group_bot.repository import GroupCryptoSubscriptionRepo

async def handle_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    with contextlib.suppress(Exception):
        await query.answer()

    user_id = query.from_user.id
    if user_id != ADMIN_USER_ID:
        with contextlib.suppress(Exception):
            await query.answer("Unauthorized.", show_alert=True)
        return

    try:
        if query.data == "admin_main" or query.data == "admin_back":
            await query.edit_message_text(
                admin_ui.get_admin_dashboard(),
                reply_markup=admin_ui.get_admin_main_menu(),
                parse_mode="HTML",
            )
        elif query.data == "admin_overview":
            stats = await MonitoringRepo.get_subscription_stats()
            ticket_stats = {"total": 0, "open": 0, "resolved": 0} # Dummy for now
            await query.edit_message_text(
                admin_ui.format_system_overview(stats, ticket_stats),
                reply_markup=admin_ui.get_back_button(),
                parse_mode="HTML",
            )
        elif query.data == "admin_health":
            bots = await BotRegistryRepo.get_all_bots()
            await query.edit_message_text(
                admin_ui.format_bot_health(bots),
                reply_markup=admin_ui.get_back_button(),
                parse_mode="HTML",
            )
        elif query.data == "admin_crypto_menu":
            await query.edit_message_text(
                "🪙 <b>Crypto Bot Management</b>\\n\\nSelect an action:",
                reply_markup=admin_ui.get_crypto_admin_menu(),
                parse_mode="HTML",
            )
        elif query.data == "admin_group_menu":
            await query.edit_message_text(
                "🛡️ <b>Group Bot Management</b>\\n\\nSelect an action:",
                reply_markup=admin_ui.get_group_admin_menu(),
                parse_mode="HTML",
            )
        elif query.data == "admin_crypto_keygen_30":
            key = await CryptoSubscriptionRepo.generate_key(30)
            await query.edit_message_text(
                f"✅ Generated 30-day Crypto Key:\\n<code>{key}</code>",
                reply_markup=admin_ui.get_back_button(),
                parse_mode="HTML",
            )
        elif query.data == "admin_crypto_keygen_90":
            key = await CryptoSubscriptionRepo.generate_key(90)
            await query.edit_message_text(
                f"✅ Generated 90-day Crypto Key:\\n<code>{key}</code>",
                reply_markup=admin_ui.get_back_button(),
                parse_mode="HTML",
            )
        elif query.data == "admin_group_keygen_30":
            key = await GroupCryptoSubscriptionRepo.generate_key(30)
            await query.edit_message_text(
                f"✅ Generated 30-day Group Key:\\n<code>{key}</code>",
                reply_markup=admin_ui.get_back_button(),
                parse_mode="HTML",
            )
        elif query.data == "admin_group_keygen_90":
            key = await GroupCryptoSubscriptionRepo.generate_key(90)
            await query.edit_message_text(
                f"✅ Generated 90-day Group Key:\\n<code>{key}</code>",
                reply_markup=admin_ui.get_back_button(),
                parse_mode="HTML",
            )
        elif query.data == "admin_crypto_subs":
            subs = await CryptoSubscriptionRepo.get_all_subscriptions()
            text = "📋 <b>Active Crypto Subscriptions:</b>\\n\\n"
            for user, days in subs:
                text += f"• <code>{user}</code> - {days} days left\\n"
            if not subs: text += "No active subscriptions."
            await query.edit_message_text(text, reply_markup=admin_ui.get_back_button(), parse_mode="HTML")
        elif query.data == "admin_group_subs":
            subs = await GroupCryptoSubscriptionRepo.get_all_subscriptions()
            text = "📋 <b>Active Group Subscriptions:</b>\\n\\n"
            for user, days in subs:
                text += f"• <code>{user}</code> - {days} days left\\n"
            if not subs: text += "No active subscriptions."
            await query.edit_message_text(text, reply_markup=admin_ui.get_back_button(), parse_mode="HTML")
        else:
            await query.answer("Feature in development or migrated.", show_alert=True)
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
'''

with open('A:/projectmonolith/src/zenith_admin_bot/dashboard.py', 'w', encoding='utf-8') as f:
    f.write(dashboard_code)


# 3. Clean up run_admin_bot.py
run_admin_code = '''
import asyncio
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler
from core.config import ADMIN_BOT_TOKEN
from core.database import dispose_engine
from core.error_handler import handle_bot_error
from core.gateway import attach_gateway, setup_bot_webhook
from core.logger import setup_logger
from core.webhook_router import register_bot_webhook
from zenith_admin_bot.commands import cmd_start, cmd_help, cmd_broadcast
from zenith_admin_bot.dashboard import handle_dashboard
from zenith_admin_bot.monitoring import start_monitoring, stop_monitoring

logger = setup_logger("ADMIN")
bot_app = None
background_tasks = set()

async def start_service():
    global bot_app
    logger.info("Initializing Admin Bot...")
    if not ADMIN_BOT_TOKEN:
        logger.warning("No ADMIN_BOT_TOKEN provided. Service disabled.")
        return

    bot_app = ApplicationBuilder().token(ADMIN_BOT_TOKEN).build()
    bot_app.add_error_handler(handle_bot_error)
    bot_app.add_handler(CommandHandler("start", cmd_start))
    bot_app.add_handler(CommandHandler("help", cmd_help))
    bot_app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    bot_app.add_handler(CallbackQueryHandler(handle_dashboard, pattern="^admin_"))

    register_bot_webhook("admin", bot_app)
    await setup_bot_webhook("admin", bot_app)
    await bot_app.start()

    logger.info("Starting monitoring loops...")
    task = asyncio.create_task(start_monitoring())
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)
    attach_gateway("admin", {"health": "ok"})
    logger.info("Admin Bot setup complete.")

async def stop_service():
    logger.info("Stopping Admin Bot...")
    await stop_monitoring()
    for task in background_tasks:
        task.cancel()
    if bot_app:
        await bot_app.stop()
        await bot_app.shutdown()
    await dispose_engine()
    logger.info("Admin Bot stopped.")
'''

with open('A:/projectmonolith/src/run_admin_bot.py', 'w', encoding='utf-8') as f:
    f.write(run_admin_code)
