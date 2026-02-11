import asyncio
import logging
import signal
import sys

from pipeline.ingest_pipeline import start_pipeline
from bot.telegram_app import start_bot
from database.init_db import init_db


# ===== LOGGING =====
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

logger = logging.getLogger("MAIN")


# ===== GRACEFUL SHUTDOWN SUPPORT =====
shutdown_event = asyncio.Event()


def shutdown_handler():
    logger.warning("SHUTDOWN SIGNAL RECEIVED")
    shutdown_event.set()


async def main():

    logger.info("🚀 TELEACADEMIC BOT STARTING")

    # ===== INIT DATABASE =====
    init_db()
    logger.info("DATABASE READY")

    # ===== START PIPELINE BACKGROUND =====
    pipeline_task = asyncio.create_task(start_pipeline())
    logger.info("PIPELINE TASK STARTED")

    # ===== START TELEGRAM =====
    bot_task = asyncio.create_task(start_bot())
    logger.info("TELEGRAM TASK STARTED")

    # ===== WAIT FOR SHUTDOWN =====
    await shutdown_event.wait()

    logger.warning("SHUTTING DOWN TASKS...")

    pipeline_task.cancel()
    bot_task.cancel()

    await asyncio.gather(pipeline_task, bot_task, return_exceptions=True)

    logger.info("BOT STOPPED CLEANLY")


if __name__ == "__main__":

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # ===== SIGNAL HANDLERS =====
    try:
        loop.add_signal_handler(signal.SIGINT, shutdown_handler)
        loop.add_signal_handler(signal.SIGTERM, shutdown_handler)
    except NotImplementedError:
        # Windows safe fallback
        pass

    try:
        loop.run_until_complete(main())
    finally:
        loop.close()
        sys.exit(0)
