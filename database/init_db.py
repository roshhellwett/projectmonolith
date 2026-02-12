import asyncio
import logging
from database.db import Base, engine
from database import models 

logger = logging.getLogger("DATABASE_INIT")

async def init_db():
    """
    Supreme Async Init:
    Uses run_sync to allow the AsyncEngine to create tables[cite: 71].
    """
    logger.info("Verifying database tables...")
    try:
        async with engine.begin() as conn:
            # run_sync is required to bridge the async engine with sync metadata [cite: 72]
            await conn.run_sync(Base.metadata.create_all)
        logger.info("DATABASE TABLES CREATED / VERIFIED")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise e