import asyncio
import logging
from datetime import datetime

from scraper.makaut_scraper import scrape_all_sources
from database.db import SessionLocal
from database.models import Notification
from delivery.broadcaster import broadcast
from core.config import SCRAPE_INTERVAL
from bot.telegram_app import is_bot_ready   # ⭐ IMPORTANT

logger = logging.getLogger("PIPELINE")


async def start_pipeline():

    logger.info("PIPELINE STARTED")

    while True:
        db = None

        try:
            logger.info("SCRAPE CYCLE START")

            # ===== SCRAPE =====
            items = scrape_all_sources()
            total_scraped = len(items)

            logger.info(f"SCRAPED {total_scraped} ITEMS")

            if not items:
                logger.warning("NO ITEMS SCRAPED")
                await asyncio.sleep(SCRAPE_INTERVAL)
                continue

            # ===== DB SESSION =====
            db = SessionLocal()

            # ===== LOAD HASHES (LOW DB LOAD) =====
            existing_hashes = {
                h for (h,) in db.query(Notification.content_hash).all()
            }

            new_notifications = []
            inserted_count = 0

            # ===== PROCESS ITEMS =====
            for item in items:
                try:
                    content_hash = item.get("content_hash")

                    if not content_hash:
                        continue

                    if content_hash in existing_hashes:
                        continue

                    # Ensure timestamps exist
                    item.setdefault("scraped_at", datetime.utcnow())
                    item.setdefault("published_date", datetime.utcnow())

                    notif = Notification(**item)
                    db.add(notif)

                    new_notifications.append(item)
                    existing_hashes.add(content_hash)
                    inserted_count += 1

                except Exception as item_error:
                    logger.warning(f"ITEM FAILED {item_error}")

            # ===== COMMIT ONCE =====
            if inserted_count > 0:
                db.commit()

            logger.info(f"PIPELINE STORED {inserted_count} NEW")

            # ⭐⭐⭐ READY SAFE BROADCAST ⭐⭐⭐
            if new_notifications:

                logger.info(
                    f"BROADCASTING {len(new_notifications)} NEW NOTIFICATIONS"
                )

                # Wait until telegram bot ready
                while not is_bot_ready():
                    logger.info("WAITING TELEGRAM READY...")
                    await asyncio.sleep(2)

                await broadcast(new_notifications)

        except Exception as e:
            logger.error(f"PIPELINE ERROR {e}", exc_info=True)

        finally:
            if db:
                db.close()

        logger.info("SCRAPE CYCLE DONE")

        await asyncio.sleep(SCRAPE_INTERVAL)
