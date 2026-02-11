import asyncio
import logging
import sys

from core.logger import setup_logger
from database.init_db import init_db
from bot.telegram_app import start_telegram
from pipeline.ingest_pipeline import start_pipeline

logger = logging.getLogger("MAIN")

async def main():
    setup_logger()
    logger.info("🚀 TELEACADEMIC CHANNEL BOT STARTING")

    # ===== DATABASE INIT =====
    try:
        init_db()
    except Exception as e:
        logger.critical(f"DATABASE INIT FAILED: {e}")
        sys.exit(1)

    # ===== START TELEGRAM FIRST =====
    try:
        await start_telegram()
    except Exception as e:
        logger.critical(f"TELEGRAM START FAILED: {e}")
        sys.exit(1)

    # ===== START PIPELINE BACKGROUND =====
    pipeline_task = asyncio.create_task(start_pipeline())

    logger.info("SYSTEM READY")

    # ===== KEEP PROCESS ALIVE =====
    try:
        # Wait on the pipeline task.
        await pipeline_task
    except asyncio.CancelledError:
        logger.info("Bot stopping...")
    except Exception as e:
        logger.critical(f"PIPELINE CRASHED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass