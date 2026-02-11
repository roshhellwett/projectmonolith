import asyncio
import logging
from telegram.ext import ApplicationBuilder

from core.config import BOT_TOKEN
from bot.user_handlers import register_user_handlers

logger = logging.getLogger("TELEGRAM")

_app = None
_ready = False   # ⭐ READY FLAG


def get_bot():
    """
    Safe accessor for broadcaster layer
    """
    if not _ready:
        raise RuntimeError("Telegram bot not ready yet")
    return _app.bot


def is_bot_ready():
    return _ready


async def start_bot():
    """
    Production-safe Telegram bootstrap
    """

    global _app, _ready

    logger.info("STARTING TELEGRAM BOT")

    # ===== BUILD APP =====
    _app = ApplicationBuilder().token(BOT_TOKEN).build()

    # ===== REGISTER HANDLERS =====
    register_user_handlers(_app)
    logger.info("ALL HANDLERS REGISTERED")

    # ===== START TELEGRAM =====
    await _app.initialize()
    await _app.start()

    _ready = True   # ⭐ BOT READY NOW
    logger.info("TELEGRAM BOT READY")

    # ===== KEEP ALIVE =====
    try:
        while True:
            await asyncio.sleep(3600)

    finally:
        logger.info("STOPPING TELEGRAM BOT")
        await _app.stop()
        await _app.shutdown()
