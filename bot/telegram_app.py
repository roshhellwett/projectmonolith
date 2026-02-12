import logging
from telegram.ext import ApplicationBuilder, CommandHandler
from core.config import BOT_TOKEN
from bot.status import status

logger = logging.getLogger("TELEGRAM")

# Global application instance
_app = None

def get_bot():
    """
    Returns the bot instance for global use in the pipeline.
    """
    if _app is None:
        raise RuntimeError("Telegram App has not been started yet!")
    return _app.bot

async def start_telegram():
    """
    Initializes and starts the main Broadcast Bot.
    """
    global _app

    logger.info("Starting Main Broadcast Bot...")

    # Build the application with stable network settings
    _app = ApplicationBuilder().token(BOT_TOKEN).read_timeout(30).connect_timeout(30).build()

    # Register Handlers
    _app.add_handler(CommandHandler("status", status))

    # Initialize and start the bot service
    await _app.initialize()
    await _app.start()
    
    # Start polling for commands (like /status)
    await _app.updater.start_polling()

    logger.info("Main Broadcast Bot READY & POLLING")

    return _app