import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from core.config import DATABASE_URL

logger = logging.getLogger("DATABASE")

# FIX: Force the async driver even if the user provides a standard sqlite URL 
if DATABASE_URL.startswith("sqlite:///"):
    ASYNC_DB_URL = DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")
elif DATABASE_URL.startswith("sqlite://"):
    ASYNC_DB_URL = DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://")
else:
    ASYNC_DB_URL = DATABASE_URL

# ===== ASYNC ENGINE =====
# pool_pre_ping ensures the connection is alive before use 
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
logger.info(f"DATABASE ENGINE READY (ASYNC MODE: {ASYNC_DB_URL.split('+')[0]})")