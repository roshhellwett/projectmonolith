import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from core.config import DATABASE_URL

logger = logging.getLogger("DATABASE")

# Convert standard sqlite URL to async version for aiosqlite
IF_SQLITE = "sqlite" in DATABASE_URL
ASYNC_DB_URL = DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///") if IF_SQLITE else DATABASE_URL

# ===== ASYNC ENGINE =====
# pool_pre_ping ensures the connection is alive before use [cite: 60]
engine = create_async_engine(
    ASYNC_DB_URL,
    pool_pre_ping=True,
    future=True,
    echo=False
)

# ===== ASYNC SESSION FACTORY =====
# This produces sessions that support the 'async with' protocol
AsyncSessionLocal = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

Base = declarative_base()
logger.info("DATABASE ENGINE READY")