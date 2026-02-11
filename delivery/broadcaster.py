import asyncio
import logging
from database.db import SessionLocal
from database.models import Subscriber
from pipeline.message_formatter import format_message
from bot.telegram_app import get_bot

logger = logging.getLogger("BROADCASTER")


async def broadcast(notifications):

    bot = get_bot()

    db = SessionLocal()
    subs = db.query(Subscriber).filter_by(active=True).all()

    success = 0
    failed = 0

    for n in notifications:

        msg = format_message(n)

        for sub in subs:
            try:
                await bot.send_message(
                    chat_id=sub.telegram_id,
                    text=msg,
                    disable_web_page_preview=False
                )

                success += 1
                await asyncio.sleep(0.05)

            except Exception as e:
                failed += 1
                logger.error(f"BROADCAST FAIL {sub.telegram_id} {e}")

    db.close()

    logger.info(f"BROADCAST DONE success={success} failed={failed}")
