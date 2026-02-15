import asyncio
from core.task_manager import supervised_task
from core.logger import setup_logger
from zenith_group_bot.group_app import start_group_bot
from zenith_group_bot.repository import dispose_group_engine

logger = setup_logger("PRODUCTION")

async def main():
    logger.info("🚀 ZENITH SUPREME EDITION: CLUSTER START")
    try:
        await asyncio.gather(
            supervised_task("GROUP_MONITOR", start_group_bot)
        )
    except asyncio.CancelledError:
        logger.info("🛑 Task Gather Cancelled.")
    finally:
        logger.info("🛑 Executing Graceful Cloud Shutdown Sequence...")
        await dispose_group_engine()
        logger.info("✅ Disconnected from database safely.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Process Interrupted. Exiting.")