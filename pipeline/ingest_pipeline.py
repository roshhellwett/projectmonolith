import asyncio
import logging
from datetime import datetime

from scraper.makaut_scraper import scrape_all_sources
from database.db import SessionLocal
from database.models import Notification, SystemFlag
from delivery.channel_broadcaster import broadcast_channel
from pipeline.message_formatter import format_message
from core.config import SCRAPE_INTERVAL

logger = logging.getLogger("PIPELINE")

FIRST_BOOT_LIMIT = 20
HASH_CACHE_LIMIT = 5000


async def start_pipeline():

    logger.info("PIPELINE STARTED")

    # ===== WAIT TELEGRAM READY =====
    await asyncio.sleep(5)

    while True:

        db = None

        try:
            logger.info("SCRAPE CYCLE START")

            items = scrape_all_sources()

            if not items:
                await asyncio.sleep(SCRAPE_INTERVAL)
                continue

            db = SessionLocal()

            # ===== LIMIT HASH CACHE SIZE =====
            existing_hashes = {
                h for (h,) in db.query(Notification.content_hash)
                .order_by(Notification.id.desc())
                .limit(HASH_CACHE_LIMIT)
                .all()
            }

            new_notifications = []
            notifications_to_save = []

            for item in items:
                h = item.get("content_hash")
                if not h or h in existing_hashes:
                    continue

                # Ensure defaults
                item.setdefault("scraped_at", datetime.utcnow())
                item.setdefault("published_date", datetime.utcnow())

                # Prepare DB object but DO NOT ADD yet
                notif = Notification(**item)
                notifications_to_save.append(notif)
                
                new_notifications.append(item)
                existing_hashes.add(h)

            logger.info(f"NEW NOTIFICATIONS {len(new_notifications)}")

            if not new_notifications:
                db.close() # Close manually if continuing
                await asyncio.sleep(SCRAPE_INTERVAL)
                continue

            # ===== FIRST RUN CHECK =====
            first_flag = db.query(SystemFlag).filter_by(key="FIRST_RUN_DONE").first()
            
            msgs_to_send = []

            if not first_flag:
                logger.info("FIRST BOOT MODE ACTIVE - LIMITING BROADCAST")
                limited_items = new_notifications[:FIRST_BOOT_LIMIT]
                msgs_to_send = [format_message(n) for n in limited_items]
                
                # Mark first run as done
                db.add(SystemFlag(key="FIRST_RUN_DONE", value="1"))
            else:
                msgs_to_send = [format_message(n) for n in new_notifications]

            # ===== 1. BROADCAST FIRST =====
            # We send first. If we crash here, we haven't saved to DB yet, 
            # so we will retry next loop. This prevents "Saved but not Sent" bug.
            if msgs_to_send:
                await broadcast_channel(msgs_to_send)

            # ===== 2. SAVE TO DB AFTER SENDING =====
            for n_obj in notifications_to_save:
                db.add(n_obj)
            
            db.commit()
            logger.info("DB SYNC COMPLETE")

        except Exception as e:
            logger.error(f"PIPELINE ERROR {e}", exc_info=True)
            if db:
                db.rollback()

        finally:
            if db:
                db.close()

        logger.info("SCRAPE CYCLE DONE")
        await asyncio.sleep(SCRAPE_INTERVAL)