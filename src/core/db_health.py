"""
Database health monitoring for Project Monolith.

Provides:
- Periodic connection pool stats logging
- Connection health ping
- Slow query detection
- Pool exhaustion alerting
"""

import asyncio
import time

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from core.logger import setup_logger

logger = setup_logger("DB_HEALTH")

_health_task: asyncio.Task | None = None
_is_healthy: bool = True


async def check_connection_health(engine: AsyncEngine) -> tuple[bool, float]:
    """
    Ping the database and measure latency.

    Returns (is_healthy, latency_ms).
    """
    start = time.monotonic()
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        latency = (time.monotonic() - start) * 1000
        return True, round(latency, 2)
    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        logger.error(f"DB health check failed ({latency:.0f}ms): {e}")
        return False, round(latency, 2)


def get_pool_stats(engine: AsyncEngine) -> dict:
    """Get connection pool statistics."""
    try:
        pool = engine.pool
        return {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalid": pool.status(),
        }
    except Exception as e:
        logger.warning(f"Could not get pool stats: {e}")
        return {"error": str(e)}


async def health_monitor_loop(engine: AsyncEngine, interval: int = 300):
    """
    Background loop that monitors database health.

    Runs every `interval` seconds. Logs pool stats and connection latency.
    """
    global _is_healthy

    while True:
        try:
            healthy, latency = await check_connection_health(engine)
            _is_healthy = healthy

            stats = get_pool_stats(engine)

            if healthy:
                if latency > 1000:
                    logger.warning(f"⚠️ DB latency high: {latency}ms | Pool: {stats}")
                else:
                    logger.debug(f"💚 DB healthy: {latency}ms | Pool: {stats}")
            else:
                logger.error(f"🔴 DB unhealthy: {latency}ms | Pool: {stats}")

            # Warn if pool is nearly exhausted
            checked_out = stats.get("checked_out", 0)
            pool_size = stats.get("pool_size", 1)
            if isinstance(checked_out, int) and isinstance(pool_size, int) and pool_size > 0:
                utilization = checked_out / pool_size
                if utilization > 0.8:
                    logger.warning(
                        f"⚠️ Connection pool {utilization:.0%} utilized "
                        f"({checked_out}/{pool_size})"
                    )

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Health monitor error: {e}")

        await asyncio.sleep(interval)


async def start_health_monitor(engine: AsyncEngine, interval: int = 300):
    """Start the background health monitor."""
    global _health_task
    if _health_task is not None:
        return
    _health_task = asyncio.create_task(health_monitor_loop(engine, interval))
    logger.info("💚 Database health monitor started")


async def stop_health_monitor():
    """Stop the background health monitor."""
    global _health_task
    if _health_task:
        _health_task.cancel()
        try:
            await _health_task
        except asyncio.CancelledError:
            pass
        _health_task = None
    logger.info("🛑 Database health monitor stopped")


def is_db_healthy() -> bool:
    """Check if the database was healthy at last check."""
    return _is_healthy
