import logging
from telegram.ext import ApplicationBuilder, CommandHandler
from core.config import BOT_TOKEN
from bot.status import status

logger = logging.getLogger("TELEGRAM")

_app = None


def get_bot():
    if _app is None:
        raise RuntimeError("Telegram not started yet")
    return _app.bot


async def start_telegram():
    global _app

    logger.info("Starting Telegram App")

    _app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Register Handlers
    _app.add_handler(CommandHandler("status", status))

    await _app.initialize()
    await _app.start()
    
    # IMPORTANT: Start receiving updates (polling) for commands to work
    await _app.updater.start_polling()

    logger.info("Telegram READY & POLLING")

    return _app