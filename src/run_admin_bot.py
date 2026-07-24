
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
    await bot_app.initialize()
    await bot_app.start()

    logger.info("Starting monitoring loops...")
    task = asyncio.create_task(start_monitoring(bot_app))
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)
    logger.info("Admin Bot setup complete.")

async def register_webhook():
    if bot_app:
        await setup_bot_webhook(bot_app, "admin")

async def stop_service(dispose_db: bool = False):
    logger.info("Stopping Admin Bot...")
    await stop_monitoring()
    for task in background_tasks:
        task.cancel()
    if bot_app:
        await bot_app.stop()
        await bot_app.shutdown()
    await dispose_engine()
    logger.info("Admin Bot stopped.")
