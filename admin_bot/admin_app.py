import os
import logging
from telegram.ext import ApplicationBuilder, CommandHandler
# Added health_check to the import list
from admin_bot.handlers import update_system, send_db_backup, health_check

logger = logging.getLogger("ADMIN_BOT")

async def start_admin_bot():
    token = os.getenv("ADMIN_BOT_TOKEN")
    if not token:
        logger.error("ADMIN_BOT_TOKEN missing in .env!")
        return

    app = ApplicationBuilder().token(token).build()
    
    # Register management commands
    app.add_handler(CommandHandler("update", update_system))
    app.add_handler(CommandHandler("backup", send_db_backup))
    # NEW: Register the health check command
    app.add_handler(CommandHandler("health", health_check))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    logger.info("ADMIN CONTROL BOT READY & POLLING")