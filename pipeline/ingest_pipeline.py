import asyncio
import logging
from datetime import datetime
from sqlalchemy import text
from scraper.makaut_scraper import scrape_source, get_source_health
from core.sources import URLS
from database.db import SessionLocal
from database.models import Notification
from delivery.channel_broadcaster import broadcast_channel
from pipeline.message_formatter import format_message
from core.config import SCRAPE_INTERVAL, ADMIN_ID
from bot.telegram_app import get_bot

logger = logging.getLogger("PIPELINE")

async def start_pipeline():
    """Main background task with context-managed DB sessions[cite: 101, 102]."""
    logger.info("🚀 SECURE ASYNC PIPELINE STARTED")
    while True:
        try:
            # 1. Scrape each source individually to isolate errors [cite: 106]
            for key, config in URLS.items():
                items = await scrape_source(key, config)
                
                if not items: continue

                # 2. Context manager for DB session [cite: 101]
                async with SessionLocal() as db:
                    for item in items:
                        exists = db.query(Notification.id).filter_by(content_hash=item['content_hash']).first() [cite: 102]
                        if not exists:
                            db.add(Notification(**item))
                            await db.commit()
                            await broadcast_channel([format_message(item)])
                
                await asyncio.sleep(2) # Politeness delay
            
            # 3. Health Monitoring
            health = get_source_health()
            for src, fails in health.items():
                if fails >= 3:
                    bot = get_bot()
                    await bot.send_message(ADMIN_ID, f"🚨 <b>Source Failure</b>: {src} unreachable.")
                
        except Exception as e:
            logger.error(f"Global Pipeline Loop Error: {e}")
        
        await asyncio.sleep(int(SCRAPE_INTERVAL))