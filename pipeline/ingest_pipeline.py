import asyncio
import logging
from sqlalchemy import select
from scraper.makaut_scraper import scrape_source, get_source_health
from core.sources import URLS
from database.db import AsyncSessionLocal
from database.models import Notification
from delivery.channel_broadcaster import broadcast_channel
from pipeline.message_formatter import format_message
from core.config import SCRAPE_INTERVAL, ADMIN_ID
from bot.telegram_app import get_bot

logger = logging.getLogger("PIPELINE")

async def start_pipeline():
    logger.info("🚀 SUPREME ASYNC PIPELINE STARTED")
    while True:
        try:
            for key, config in URLS.items():
                items = await scrape_source(key, config)
                if not items: continue

                # Properly using async context manager for non-blocking I/O
                async with AsyncSessionLocal() as db:
                    for item in items:
                        # Async execution of the existence check
                        stmt = select(Notification.id).where(Notification.content_hash == item['content_hash'])
                        result = await db.execute(stmt)
                        exists = result.scalar()

                        if not exists:
                            db.add(Notification(**item))
                            await db.commit() # Non-blocking commit
                            await broadcast_channel([format_message(item)])
                
                await asyncio.sleep(2) # Politeness delay between sources
            
            # Health Monitoring [cite: 105]
            health = get_source_health()
            for src, fails in health.items():
                if fails >= 3:
                    await get_bot().send_message(ADMIN_ID, f"🚨 Source {src} is DOWN!")
                
        except Exception as e:
            logger.error(f"Global Pipeline Loop Error: {e}")
        
        await asyncio.sleep(int(SCRAPE_INTERVAL))