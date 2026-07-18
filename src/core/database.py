import asyncio
import functools

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from core.config import DATABASE_URL, DB_POOL_SIZE
from core.logger import setup_logger

logger = setup_logger("DATABASE")

Base = declarative_base()

_engine: AsyncEngine | None = None
AsyncSessionLocal: sessionmaker | None = None


def _resolve_database_url(url: str) -> str:
    if not url:
        raise ValueError("DATABASE_URL is not set")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and "asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("sqlite"):
        return url
    elif not url.startswith("postgresql+asyncpg://"):
        raise ValueError(f"Unsupported DATABASE_URL scheme: {url.split('://')[0]}")
    return url


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        resolved_url = _resolve_database_url(DATABASE_URL)
        if resolved_url.startswith("sqlite"):
            _engine = create_async_engine(resolved_url)
        else:
            _engine = create_async_engine(
                resolved_url,
                pool_size=DB_POOL_SIZE,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=3600,
            )
        logger.info("Database engine created")
    return _engine


def get_session() -> sessionmaker:
    global AsyncSessionLocal
    if AsyncSessionLocal is None:
        AsyncSessionLocal = sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return AsyncSessionLocal


async def init_db():
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("All database tables created")


async def dispose_engine():
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        logger.info("Database engine disposed")


def db_retry(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        for attempt in range(3):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if attempt == 2:
                    raise
                logger.warning(f"DB retry {attempt + 1}/3 in {func.__name__}: {e}")
                await asyncio.sleep(0.5 * (2**attempt))

    return wrapper
