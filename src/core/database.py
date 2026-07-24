import asyncio
import contextlib
import functools
import re
from collections.abc import AsyncGenerator

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
    elif url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("sqlite"):
        return url
    elif not url.startswith("postgresql+asyncpg://"):
        raise ValueError(f"Unsupported DATABASE_URL scheme: {url.split('://')[0]}")
    url = re.sub(r"([?&])(pgbouncer|connection_limit|pool_timeout)=[^&]+(&|$)", r"\1", url, flags=re.IGNORECASE)
    url = re.sub(r"[?&]$", "", url)
    return url


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        raw_url = DATABASE_URL or ""
        use_pgbouncer = "pgbouncer=true" in raw_url.lower()
        
        resolved_url = _resolve_database_url(raw_url)
        if resolved_url.startswith("sqlite"):
            _engine = create_async_engine(resolved_url, echo=False)
        else:
            # If using PgBouncer, statement caching must be 0. Otherwise, use defaults.
            connect_args = {"statement_cache_size": 0} if use_pgbouncer else {}
            execution_options = {"prepared_statement_cache_size": 0} if use_pgbouncer else {}
            
            _engine = create_async_engine(
                resolved_url,
                pool_size=max(5, DB_POOL_SIZE),
                max_overflow=max(10, DB_POOL_SIZE * 2),
                pool_pre_ping=True,
                pool_recycle=300,  # Refresh connections sooner (5 minutes) for cloud DBs
                pool_timeout=30,
                pool_use_lifo=True,
                connect_args=connect_args,
                execution_options=execution_options,
            )
        logger.info("Database engine created (PgBouncer=%s)", use_pgbouncer)
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


@contextlib.asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Context manager that provides a session with query timeout and auto-cleanup.

    Usage:
        async with get_db() as session:
            result = await session.execute(stmt)
    """
    session = get_session()()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


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
                    logger.error(
                        f"\n┌── 🚨 SECTOR ERROR DIAGNOSTIC ──┐\n"
                        f"│ Sector:   DATABASE ({func.__name__})\n"
                        f"│ Error:    {error_name}: {e}\n"
                        f"└────────────────────────────────┘"
                    )
                    raise
                last_error = e
                logger.warning(f"DB retry {attempt + 1}/3 in {func.__name__}: {error_name}: {e}")
                await asyncio.sleep(0.5 * (2**attempt))
        if last_error is not None:
            raise last_error
        raise RuntimeError(f"Database operation {func.__name__} failed after retries")

    return wrapper


_init_lock: asyncio.Lock | None = None


def _get_init_lock() -> asyncio.Lock:
    global _init_lock
    if _init_lock is None:
        _init_lock = asyncio.Lock()
    return _init_lock


@db_retry
async def init_db():
    async with _get_init_lock():
        import core.rate_limit_models  # noqa: F401
        import zenith_admin_bot.models  # noqa: F401
        import zenith_ai_bot.models  # noqa: F401
        import zenith_crypto_bot.models  # noqa: F401
        import zenith_group_bot.models  # noqa: F401

        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("All database tables checked/created")


_dispose_lock: asyncio.Lock | None = None


def _get_dispose_lock() -> asyncio.Lock:
    global _dispose_lock
    if _dispose_lock is None:
        _dispose_lock = asyncio.Lock()
    return _dispose_lock


async def dispose_engine():
    global _engine, _sessionmaker_instance
    async with _get_dispose_lock():
        if _engine is not None:
            await _engine.dispose()
            _engine = None
            _sessionmaker_instance = None
            logger.info("Database engine disposed")
