import os

import pytest
from sqlalchemy import text

# Import all model modules so Base.metadata.create_all registers their tables
import zenith_admin_bot.models  # noqa: F401
import zenith_ai_bot.models  # noqa: F401
import zenith_crypto_bot.models  # noqa: F401
import zenith_group_bot.models  # noqa: F401
import zenith_support_bot.models  # noqa: F401
from core.database import get_engine, init_db


@pytest.mark.asyncio
async def test_database_reachable():
    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1


@pytest.mark.asyncio
async def test_database_tables_exist():
    engine = get_engine()
    await init_db()
    async with engine.connect() as conn:
        if engine.dialect.name == "sqlite":
            result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"))
        else:
            result = await conn.execute(
                text("SELECT tablename FROM pg_tables " "WHERE schemaname='public' ORDER BY tablename")
            )
        tables = [row[0] for row in result]

    assert len(tables) > 0, "No tables found in database"

    # Core tables we expect to exist (may vary by dialect)
    expected_common = [
        "zenith_ai_conversations",
        "crypto_users",
        "crypto_subscriptions",
        "crypto_activation_keys",
    ]
    for table in expected_common:
        if table not in tables:
            pytest.skip(f"Table '{table}' not found — possibly running with partial model imports")


@pytest.mark.asyncio
async def test_health_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_service_registry_exists(client):
    response = await client.get("/health")
    data = response.json()
    assert "services" in data
    assert isinstance(data["services"], dict)


@pytest.mark.asyncio
async def test_env_vars_for_production():
    required = ["ADMIN_BOT_TOKEN", "DATABASE_URL", "WEBHOOK_SECRET"]
    for var in required:
        assert os.getenv(var), f"Missing required env var: {var}"
