import asyncio
import functools
import re

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from core.config import DATABASE_URL, DB_POOL_SIZE
from core.logger import setup_logger

logger = setup_logger("DATABASE")

Base = declarative_base()

_engine: AsyncEngine | None = None
_sessionmaker_instance: sessionmaker | None = None


class LazyAsyncSessionMaker:
    """Lazy session maker that acquires a live session dynamically when called or entered."""

    def __call__(self, *args, **kwargs) -> AsyncSession:
        sm = get_session()
        return sm(*args, **kwargs)


AsyncSessionLocal: LazyAsyncSessionMaker = LazyAsyncSessionMaker()


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
    url = re.sub(r"\?pgbouncer=true", "", url)
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
                max_overflow=2,
                pool_pre_ping=True,
                pool_recycle=3600,
                pool_timeout=5,
                pool_use_lifo=True,
                connect_args={
                    "prepared_statement_cache_size": 0,
                    "statement_cache_size": 0,
                },
            )
        logger.info("Database engine created")
    return _engine




def get_session() -> sessionmaker:
    global _sessionmaker_instance
    if _sessionmaker_instance is None:
        _sessionmaker_instance = sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _sessionmaker_instance


async def init_db():
    from sqlalchemy import inspect
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        def _ensure_columns(connection):
            insp = inspect(connection)
            tables = insp.get_table_names()
            if "crypto_users" in tables:
                cols = [c["name"] for c in insp.get_columns("crypto_users")]
                if "groq_api_key" not in cols:
                    connection.exec_driver_sql("ALTER TABLE crypto_users ADD COLUMN groq_api_key VARCHAR(200)")
            if "zenith_group_settings" in tables:
                cols = [c["name"] for c in insp.get_columns("zenith_group_settings")]
                if "raid_mode" not in cols:
                    if engine.dialect.name == "sqlite":
                        connection.exec_driver_sql("ALTER TABLE zenith_group_settings ADD COLUMN raid_mode BOOLEAN DEFAULT 0")
                    else:
                        connection.exec_driver_sql("ALTER TABLE zenith_group_settings ADD COLUMN raid_mode BOOLEAN DEFAULT FALSE")
                if "raid_expires_at" not in cols:
                    connection.exec_driver_sql("ALTER TABLE zenith_group_settings ADD COLUMN raid_expires_at TIMESTAMP")

        await conn.run_sync(_ensure_columns)
    logger.info("All database tables and columns checked/created")


async def dispose_engine():
    global _engine, _sessionmaker_instance
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _sessionmaker_instance = None
        logger.info("Database engine disposed")


def db_retry(func):
    """Retry decorator for database operations. Only retries on connection/operational errors."""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        last_error = None
        for attempt in range(3):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error_name = type(e).__name__
                retryable = isinstance(e, ConnectionError | OSError | TimeoutError | asyncio.TimeoutError) or (
                    error_name
                    in (
                        "OperationalError",
                        "InterfaceError",
                        "DisconnectionError",
                        "ConnectionRefusedError",
                        "ConnectionDoesNotExistError",
                        "ConnectionError",
                        "InternalError",
                        "InvalidCachedStatementError",
                        "PoolError",
                    )
                )
                if not retryable or attempt == 2:
                    raise
                last_error = e
                logger.warning(f"DB retry {attempt + 1}/3 in {func.__name__}: {error_name}: {e}")
                await asyncio.sleep(0.5 * (2**attempt))
        if last_error is not None:
            raise last_error
        raise RuntimeError(f"Database operation {func.__name__} failed after retries")

    return wrapper

