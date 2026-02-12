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
        cycle_start = asyncio.get_event_loop().time()
        try:
            for key, config in URLS.items():
                items = await scrape_source(key, config)
                if not items: continue

                async with AsyncSessionLocal() as db:
                    new_count = 0
                    for item in items:
                        stmt = select(Notification.id).where(Notification.content_hash == item['content_hash'])
                        result = await db.execute(stmt)
                        if not result.scalar():
                            db.add(Notification(**item))
                            await db.commit() 
                            await broadcast_channel([format_message(item)])
                            new_count += 1
                await asyncio.sleep(3) # Anti-flood delay
            
            # Health Check
            health = get_source_health()
            for src, fails in health.items():
                if fails >= 3:
                    bot = get_bot()
                    await bot.send_message(ADMIN_ID, f"🚨 <b>SOURCE DOWN</b>: {src}")
                
        except Exception as e:
            logger.error(f"❌ PIPELINE ERROR: {e}")
        
        sleep_time = max(10, SCRAPE_INTERVAL - (asyncio.get_event_loop().time() - cycle_start))
        await asyncio.sleep(sleep_time)
         #@academictelebotbyroshhellwett